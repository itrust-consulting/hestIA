import { writable, get } from 'svelte/store';
import {
  messages,
  removeMessage,
  updateMessage,
  findIndex,
  buildAPIMessages,
} from '$lib/stores/chat';

import { activeConversationId, loadConversations, forceEvictStaleHeadNow } from '$lib/stores/conversations';
import { setContextBudget } from '$lib/stores/contextBudget';
import { activeCorpusName } from '$lib/stores/isms';
import { api } from '$lib/api/client';
import type { ContentPart } from '$lib/types';

export const sending = writable<boolean>(false);

export type ParsedAttachment = { name: string; markdown: string; size?: number };
export type ImageAttachment  = { dataUrl: string; name: string; size?: number };

let controller: AbortController | null = null;

export function stop() {
  controller?.abort();
}

function tempId() {
  return '__local__' + crypto.randomUUID();
}

export async function sendMessage(
  text: string,
  attachments: ParsedAttachment[] = [],
  images: ImageAttachment[] = [],
) {
  if ((!text.trim() && !attachments.length && !images.length) || get(sending)) return;

  sending.set(true);

  // a new turn is starting — don't hang on to abandoned scrollback history
  forceEvictStaleHeadNow();

  const userTempId = tempId();

  let apiContent: string | ContentPart[] | undefined;
  if (images.length > 0) {
    const parts: ContentPart[] = [];
    if (attachments.length > 0) {
      const blocks = attachments
        .map(a => `<document name="${a.name}">\n${a.markdown}\n</document>`)
        .join('\n\n');
      parts.push({ type: 'text', text: text.trim() ? `${blocks}\n\n${text}` : blocks });
    } else if (text.trim()) {
      parts.push({ type: 'text', text });
    }
    for (const img of images) {
      parts.push({ type: 'image_url', image_url: { url: img.dataUrl } });
    }
    apiContent = parts;
  } else if (attachments.length > 0) {
    const blocks = attachments
      .map(a => `<document name="${a.name}">\n${a.markdown}\n</document>`)
      .join('\n\n');
    apiContent = text.trim() ? `${blocks}\n\n${text}` : blocks;
  }

  messages.update(m => [
    ...m,
    {
      id: userTempId,
      role: 'user',
      content: text,
      apiContent,
      images: images.length > 0 ? images.map(i => i.dataUrl) : undefined,
      attachments: attachments.length > 0 ? attachments.map(a => ({ name: a.name, size: a.size, markdown: a.markdown })) : undefined,
      createdAt: Date.now()
    }
  ]);

  const assistantTempId = tempId();
  messages.update(m => [
    ...m,
    { id: assistantTempId, role: 'assistant', content: '', createdAt: Date.now() + 2 }
  ]);

  await streamFromHistoryInto(assistantTempId, userTempId, text, attachments.map(a => ({ name: a.name, size: a.size })));
}

export async function streamFromHistoryInto(
  assistantTempId: string,
  userTempId: string,
  displayContent?: string,
  msgAttachments?: { name: string; size?: number }[],
) {
  sending.set(true);

  controller?.abort();
  controller = new AbortController();

  try {
    const payloadMessages = buildAPIMessages();

    const res = await api.stream('/api/chat', {
      messages: payloadMessages,
      model: 'ministral-3:14b',
      model_kwargs: {},
      collection: get(activeCorpusName),
      query_kwargs: { limit: 10 },
      stream: true,
      conversation_id: get(activeConversationId),
      save_chat: true,
      ...(displayContent !== undefined ? { last_user_display_content: displayContent } : {}),
      ...(msgAttachments?.length ? { last_user_attachments: msgAttachments } : {}),
    }, controller.signal);

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    if (res.body) {
      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      let pending = '';
      let raf = 0;
      let lineBuffer = '';
      let thinkingStartedAt: number | null = null;
      let thinkingSecs: number | null = null;

      function freezeThinkingSecs() {
        if (thinkingStartedAt == null || thinkingSecs != null) return;
        thinkingSecs = Math.max(0, Math.round((Date.now() - thinkingStartedAt) / 1000));
        updateMessage(assistantTempId, { thinkingSecs });
      }

      function flushPending() {
        const chunk = pending;
        pending = '';
        raf = 0;
        if (!chunk) return;
        messages.update(m =>
          m.map(msg =>
            msg.id === assistantTempId
              ? { ...msg, content: msg.content + chunk }
              : msg
          )
        );
      }

      async function handleLine(line: string) {
        if (!line.trim()) return;
        let obj: any;
        try { obj = JSON.parse(line); } catch { return; }
        if (typeof obj.content === 'string') {
          freezeThinkingSecs();
          pending += obj.content;
          if (!raf) raf = requestAnimationFrame(flushPending);
        } else if (obj.conversation_id != null || obj.assistant_message_id != null) {
          // Final metadata frame — must be checked before thinking to avoid
          // the metadata frame (which also carries the full thinking text)
          // being mistaken for a streaming thinking chunk.
          freezeThinkingSecs();
          if (obj.conversation_id) {
            activeConversationId.set(obj.conversation_id);
            await loadConversations();
            setContextBudget(obj.used_tokens, obj.max_tokens, obj.needs_compaction);
          }
          if (obj.user_message_id) {
            updateMessage(userTempId, { id: obj.user_message_id });
          }
          if (obj.assistant_message_id) {
            updateMessage(assistantTempId, {
              id: obj.assistant_message_id,
              ...(obj.citations?.length ? { citations: obj.citations } : {}),
              ...(obj.thinking ? { thinking: obj.thinking } : {}),
            });
          } else if (obj.citations?.length || obj.thinking) {
            updateMessage(assistantTempId, {
              ...(obj.citations?.length ? { citations: obj.citations } : {}),
              ...(obj.thinking ? { thinking: obj.thinking } : {}),
            });
          }
        } else if (typeof obj.thinking === 'string') {
          if (thinkingStartedAt == null) thinkingStartedAt = Date.now();
          messages.update(m =>
            m.map(msg =>
              msg.id === assistantTempId
                ? { ...msg, thinking: (msg.thinking ?? '') + obj.thinking }
                : msg
            )
          );
        } else if (obj.status === 'compacting') {
          updateMessage(assistantTempId, { compacting: true });
        }
      }

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        lineBuffer += decoder.decode(value, { stream: true });
        const lines = lineBuffer.split('\n');
        lineBuffer = lines.pop() ?? '';
        for (const line of lines) await handleLine(line);
      }

      // Handle any remaining data not terminated by a newline
      if (lineBuffer.trim()) await handleLine(lineBuffer);

      if (raf) { cancelAnimationFrame(raf); flushPending(); }
      if (pending) flushPending();
    }
  } catch (e: any) {
    if (e.name === 'AbortError') {
      updateMessage(assistantTempId, { stopped: true });
    } else {
      updateMessage(assistantTempId, { content: `⚠️ ${e}` });
    }
  } finally {
    sending.set(false);
  }
}

export async function copyMessage(content: string) {
  try {
    await navigator.clipboard.writeText(content);
  } catch (e) {
    console.error('Clipboard error', e);
  }
}

export async function deleteMessage(id: string) {
  removeMessage(id);

  const cid = get(activeConversationId);
  if (cid) {
    await api.delete(`/api/conversations/${cid}/messages/${id}`);
  }
}

export async function retryMessage(assistantId: string) {
  if (get(sending)) return;

  // see sendMessage: a new turn is starting
  forceEvictStaleHeadNow();

  const all = get(messages);
  const cid = get(activeConversationId);

  const idx = findIndex(assistantId);
  if (idx < 0) return;
  const assistantMsg = all[idx];
  if (assistantMsg.role !== 'assistant') return;

  let userIdx = -1;
  for (let i = idx - 1; i >= 0; i--) {
    if (all[i].role === 'user') {
      userIdx = i;
      break;
    }
  }
  if (userIdx < 0) return;

  const userMsg = all[userIdx];

  if (cid) {
    // awaited: the server reconstructs history from the DB for context-budget
    // purposes, so the old turn must actually be gone before the retry's
    // request reaches it — otherwise it could still see (and fold) stale
    // messages that are about to be deleted anyway.
    await Promise.all([deleteMessage(userMsg.id), deleteMessage(assistantId)]);
  }

  const newUserTempId = tempId();
  messages.update(m => [
    ...m,
    {
      id: newUserTempId,
      role: 'user',
      content: userMsg.content,
      apiContent: userMsg.apiContent,
      images: userMsg.images,
      attachments: userMsg.attachments,
      createdAt: Date.now()
    }
  ]);

  const newAssistantTempId = tempId();
  messages.update(m => [
    ...m,
    { id: newAssistantTempId, role: 'assistant', content: '', createdAt: Date.now() + 2 }
  ]);

  await streamFromHistoryInto(
    newAssistantTempId,
    newUserTempId,
    userMsg.content,
    userMsg.attachments?.map(a => ({ name: a.name, size: a.size })),
  );
}
