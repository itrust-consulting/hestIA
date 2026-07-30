import { writable, get } from 'svelte/store';
import type { ChatMessage, ChatAPIMessages } from '$lib/types';


export const messages = writable<ChatMessage[]>([]);
export const conversationId = writable<string | null>(null);
/** True while the messages array is being mutated at the FRONT (prepending
 *  older history, or evicting the head to enforce the sliding-window cap) so
 *  <VList>'s `shift` prop can be toggled to keep the visible scroll position
 *  stable. Must stay false for end-of-list mutations (new sends, streaming,
 *  eviction from the tail). */
export const isMutatingFront = writable<boolean>(false);

export function pushMessage(role: ChatMessage['role'], content: string) {
  const msg_id = crypto.randomUUID().replace(/-/g, "");
  console.log("this is the assigned msg_id: " + msg_id) 
  messages.update((m) => [
    ...m,
    { id: msg_id, role, content, createdAt: Date.now() }
  ]);
}

export function removeMessage(id: string) {
  messages.update((m) => m.filter((x) => x.id !== id));
}

export function updateMessage(id: string, patch: Partial<ChatMessage>) {
  messages.update((m) => m.map((x) => (x.id === id ? { ...x, ...patch } : x)));
}

/** Find the index of a message by id */
export function findIndex(id: string): number {
  return get(messages).findIndex((x) => x.id === id);
}

export function clearMessages(){
    messages.set([])
}

export function buildAPIMessages(opts?: {
    limit?: number;
    includeSystem?: boolean;
    systemPrompt?: string;
}): ChatAPIMessages {
    const history = get(messages);

    const {
    limit,
    includeSystem = true,
    systemPrompt
    } = opts ?? {};

    const base: ChatAPIMessages = [];
        if (includeSystem && systemPrompt?.trim()) {
        base.push({ role: 'system', content: systemPrompt.trim() });
    }

    const trimmed = typeof limit === 'number' ? history.slice(-limit) : history;

    return [...base, ...trimmed.map(m => ({role: m.role, content: m.apiContent ?? m.content}))]
}
