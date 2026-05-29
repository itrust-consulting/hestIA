import { writable, get } from 'svelte/store';
import { tick } from 'svelte';
import { browser } from '$app/environment';
import { replaceState } from '$app/navigation';

import type { Conversation } from '$lib/types';
import { messages } from '$lib/stores/chat';
import { api } from '$lib/api/client';

function parseDocumentBlocks(content: string): Map<string, string> {
  const result = new Map<string, string>();
  const regex = /<document name="([^"]+)">\n([\s\S]*?)\n<\/document>/g;
  let match;
  while ((match = regex.exec(content)) !== null) {
    result.set(match[1], match[2]);
  }
  return result;
}

export const conversations = writable<Conversation[]>([]);
export const activeConversationId = writable<string | null>(null);
export const isLoadingMessages = writable<boolean>(false);


export async function loadConversations() {
  const res = await api.get('/api/conversations');
  if (!res.ok) throw new Error('Failed to load conversations');
  const data: Conversation[] = await res.json();
  conversations.set(data);
}

export async function openConversation(id: string) {
  activeConversationId.set(id);
  if (browser) replaceState(`/chat?cid=${id}`, {});

  isLoadingMessages.set(true);
  const res = await api.get(`/api/conversations/${id}`);
  if (!res.ok) throw new Error('Failed to load messages');

  const raw: any[] = await res.json();
  const msgs = raw.map(m => {
    const meta = typeof m.metadata === 'string' ? JSON.parse(m.metadata) : (m.metadata ?? {});
    if (m.role === 'user' && meta.display_content !== undefined) {
      const docBlocks = parseDocumentBlocks(m.content);
      const attachments = (meta.attachments ?? []).map((a: { name: string; size?: number }) => ({
        ...a,
        markdown: docBlocks.get(a.name),
      }));
      return { ...m, apiContent: m.content, content: meta.display_content, attachments };
    }
    if (m.role === 'assistant' && (meta.citations?.length || meta.thinking)) {
      return { ...m, citations: meta.citations, thinking: meta.thinking };
    }
    return m;
  });
  messages.set(msgs);
  isLoadingMessages.set(false);

  await tick();

  const container = document.querySelector('.chatbox');
  container?.scrollTo({ top: container.scrollHeight });
}

export function startNewChat() {
  activeConversationId.set(null);
  messages.set([]);
  if (browser) replaceState('/chat', {});
}

export async function renameConversation(id: string, newTitle: string) {
  const res = await api.patch(`/api/conversations/${id}`, { title: newTitle });
  if (!res.ok) throw new Error('Rename failed');
  conversations.update((list) =>
    list.map((c) => (c.id === id ? { ...c, title: newTitle } : c))
  );
}

export async function deleteConversation(id: string) {
  const res = await api.delete(`/api/conversations/${id}`);
  if (!res.ok) throw new Error('Delete failed');

  conversations.update((list) => list.filter((c) => c.id !== id));

  if (get(activeConversationId) === id) {
    startNewChat();
  }
}
