import { writable, get } from 'svelte/store';
import { tick } from 'svelte';

import type { Conversation } from '$lib/types';
import { messages } from '$lib/stores/chat';

export const conversations = writable<Conversation[]>([]);
export const activeConversationId = writable<string | null>(null);
export const isLoadingMessages = writable<boolean>(false);


export async function loadConversations() {
  const res = await fetch('/api/conversations');
  if (!res.ok) throw new Error("Failed to load conversations");
  const data: Conversation[] = await res.json();
  conversations.set(data);
}

export async function openConversation(id: string) {
  activeConversationId.set(id);

  isLoadingMessages.set(true);
  const res = await fetch(`/api/conversations/${id}`);
  if (!res.ok) throw new Error("Failed to load messages");
  
  const msgs = await res.json();
  messages.set(msgs);
  isLoadingMessages.set(false);

  await tick();

  const container = document.querySelector('.chatbox');
  container?.scrollTo({ top: container.scrollHeight })

}

export function startNewChat() {
  activeConversationId.set(null);
  messages.set([]);
}

export async function renameConversation(id: string, newTitle: string) {
  const res = await fetch(`/api/conversations/${id}`, {
    method: 'PATCH',
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title: newTitle })
  });

  if (!res.ok) throw new Error("Rename failed");

  conversations.update((list) =>
    list.map((c) => (c.id === id ? { ...c, title: newTitle } : c))
  );
}

export async function deleteConversation(id: string) {
  const res = await fetch(`/api/conversations/${id}`, {
    method: 'DELETE',
  });

  if (!res.ok) throw new Error("Delete failed");

  conversations.update((list) => list.filter((c) => c.id !== id));

  if (get(activeConversationId) === id) {
    startNewChat();
  }
}