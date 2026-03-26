import { writable, get } from 'svelte/store';
import {
  messages,
  removeMessage,
  updateMessage,
  findIndex,
  buildAPIMessages,
  pushMessage,
} from '$lib/stores/chat';
  import { activeCorpusName } from '$lib/stores/isms';

export const sending = writable<boolean>(false);

let controller: AbortController | null = null;
export function stop() {
    controller?.abort();
  }

export async function sendMessage(text: string) {
  if (!text.trim() || get(sending)) return;

  sending.set(true);

  // push user's message
  pushMessage('user', text);

  const assistantId = crypto.randomUUID();
  messages.update((m) => [
    ...m,
    { id: assistantId, role: 'assistant', content: '', createdAt: Date.now() }
  ]);
  await streamFromHistoryInto(assistantId);
}

export async function streamFromHistoryInto(targetId: string) {
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
          query_kwargs: {'limit' : 20},
          stream: true
        })
    });


    if (!res.ok) throw new Error(`HTTP ${res.json()}`);

    if (res.body) {
      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      let pending = '';
      let raf = 0;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        pending += decoder.decode(value, { stream: true });

        if (!raf) {
          raf = requestAnimationFrame(() => {
            const chunk = pending;
            pending = '';
            raf = 0;

            messages.update((m) =>
              m.map((msg) =>
                msg.id === targetId
                  ? { ...msg, content: msg.content + chunk }
                  : msg
              )
            );
          });
        }
      }

      if (pending) {
        messages.update((m) =>
          m.map((msg) =>
            msg.id === targetId
              ? { ...msg, content: msg.content + pending }
              : msg
          )
        );
      }
    }
  } catch (e: any) {
    if (e.name !== 'AbortError') {
      updateMessage(targetId, { content: `⚠️ ${e}` });
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


export function deleteMessage(id: string) {
    removeMessage(id);
}


export async function retryMessage(id: string) {
    if (get(sending)) return;

    const all = get(messages);
    const idx = findIndex(id);
    if (idx < 0) return;

    const msg = all[idx];

    // Determine the slice of history to send:
    // If retrying assistant → take history up to the previous user message (inclusive)
    // If retrying user → take history up to that user (inclusive) and remove following assistant if any.
    let sliceEnd = idx;
    if (msg.role === 'assistant') {
        // walk back to preceding user
        for (let i = idx - 1; i >= 0; i--) {
        if (all[i].role === 'user') {
            sliceEnd = i + 1; // include that user
            break;
        }
        }
    } else {
        // retrying a user: include that user itself
        sliceEnd = idx + 1;
        // option: if next is an assistant (the old answer), delete it so we “regenerate”
        if (all[idx + 1]?.role === 'assistant') {
        removeMessage(all[idx + 1].id);
        }
    }

    const kept = all.slice(0, sliceEnd);
    messages.set(kept);

    // Create a fresh assistant placeholder at the end and stream into it
    const placeholderId = crypto.randomUUID();
    messages.update((m) => [
        ...m,
        { id: placeholderId, role: 'assistant', content: '', createdAt: Date.now() }
    ]);

    await streamFromHistoryInto(placeholderId);
}
