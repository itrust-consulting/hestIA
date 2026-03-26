export type StorageNamespace = string;

export function nsForUser(userId?: string | null): StorageNamespace {
  return userId ? `hestia:user:${userId}` : `hestia:guest`;
}

export const keys = (ns: StorageNamespace) => ({
  conversations: `${ns}:conversations`,            // array of {id,title,createdAt,updatedAt?}
  convMessages: (id: string) => `${ns}:c:${id}:messages`, // array of ChatMessage
  activeId: `${ns}:activeConversationId`,
  ui: `${ns}:ui`,                                  // optional (sidebar open, theme, etc.)
  version: `${ns}:schemaVersion`
});

// src/lib/persist/local.ts
import type { ChatMessage, Conversation } from '$lib/types';

export function loadJSON<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : fallback;
  } catch {
    return fallback;
  }
}

export function saveJSON<T>(key: string, value: T) {
  try {
    localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // storage full or blocked -> swallow; you can add a toast if desired
  }
}

export const state = {
  loadConversations: (key: string) => loadJSON<Conversation[]>(key, []),
  saveConversations: (key: string, list: Conversation[]) => saveJSON(key, list),

  loadMessages: (key: string) => loadJSON<ChatMessage[]>(key, []),
  saveMessages: (key: string, msgs: ChatMessage[]) => saveJSON(key, msgs),

  loadActiveId: (key: string) => loadJSON<string | null>(key, null),
  saveActiveId: (key: string, id: string | null) => saveJSON(key, id)
};