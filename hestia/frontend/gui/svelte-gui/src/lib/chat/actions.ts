import { writable, get } from 'svelte/store';
import {
  messages,
  removeMessage,
  updateMessage,
  findIndex,
  buildAPIMessages,
} from '$lib/stores/chat';

import { activeConversationId, loadConversations } from '$lib/stores/conversations';
import { activeCorpusName } from '$lib/stores/isms';

export const sending = writable<boolean>(false);

let controller: AbortController | null = null;

export function stop() {
  controller?.abort();
}

function tempId() {
  return "__local__" + crypto.randomUUID();
}

export async function sendMessage(text: string) {
  if (!text.trim() || get(sending)) return;

  sending.set(true);

  const userTempId = tempId();
  messages.update(m => [
    ...m,
    { id: userTempId, role: 'user', content: text, createdAt: Date.now() }
  ]);

  const assistantTempId = tempId();
  messages.update(m => [
    ...m,
    { id: assistantTempId, role: 'assistant', content: '', createdAt: Date.now() + 2 }
  ]);

  await streamFromHistoryInto(assistantTempId, userTempId);
}

export async function streamFromHistoryInto(assistantTempId: string, userTempId: string) {
  sending.set(true);

  controller?.abort();
  controller = new AbortController();

  try {
    const payloadMessages = buildAPIMessages();

    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: controller.signal,
      body: JSON.stringify({
        messages: payloadMessages,
        model: 'ministral-3:14b',
        model_kwargs: {},
        collection: get(activeCorpusName),
        query_kwargs: { limit: 20 },
        stream: true,
        conversation_id: get(activeConversationId),
        save_chat: true
      })
    });

    if (!res.ok) throw new Error(`HTTP ${res.status}`);

    if (res.body) {
      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      let pending = '';
      let raf = 0;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const chunkText = decoder.decode(value, { stream: true });

        let handledAsMetadata = false;
        try {
          const maybeJson = JSON.parse(chunkText);
          if (maybeJson && typeof maybeJson === 'object') {
            
            if (maybeJson.conversation_id) {
              activeConversationId.set(maybeJson.conversation_id);
              await loadConversations();
            }

            if (maybeJson.user_message_id) {
              updateMessage(userTempId, { id: maybeJson.user_message_id });
            }

            if (maybeJson.assistant_message_id) {
              updateMessage(assistantTempId, { id: maybeJson.assistant_message_id });
            }
            handledAsMetadata = true;
          }
          
        } catch {
          // normal text chunk
        }

        if (handledAsMetadata) {
          continue;
        }

        pending += chunkText;

        if (!raf) {
          raf = requestAnimationFrame(() => {
            const chunk = pending;
            pending = '';
            raf = 0;

            messages.update(m =>
              m.map(msg =>
                msg.id === assistantTempId
                  ? { ...msg, content: msg.content + chunk }
                  : msg
              )
            );
          });
        }
      }

      if (pending) {
        messages.update(m =>
          m.map(msg =>
            msg.id === assistantTempId
              ? { ...msg, content: msg.content + pending }
              : msg
          )
        );
      }
    }
  } catch (e: any) {
    if (e.name !== 'AbortError') {
      updateMessage(assistantTempId, { content: `⚠️ ${e}` });
    }
  } finally {
    sending.set(false);
  }
}

export async function copyMessage(content: string) {
    try {
      await navigator.clipboard.writeText(content);
      // You can also show a small toast/snackbar here
    } catch (e) {
      console.error('Clipboard error', e);
    }
}

export async function deleteMessage(id: string) {
  removeMessage(id);
  
  const cid = get(activeConversationId);
  if (cid) {
    await fetch(`/api/conversations/${cid}/messages/${id}`, {
      method: 'DELETE'
    });
  }


}


export async function retryMessage(assistantId: string) {
  if (get(sending)) return;

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
    deleteMessage(userMsg.id)
    deleteMessage(assistantId)
  }

  const newUserTempId = tempId();
  messages.update(m => [
    ...m,
    { id: newUserTempId, role: "user", content: userMsg.content, createdAt: Date.now() }
  ]);


  const newAssistantTempId = tempId();
  messages.update(m => [
    ...m,
    { id: newAssistantTempId, role: "assistant", content: "", createdAt: Date.now() + 2 }
  ])
  await streamFromHistoryInto(newAssistantTempId, newUserTempId);
}