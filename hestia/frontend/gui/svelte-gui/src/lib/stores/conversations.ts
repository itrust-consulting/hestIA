import { writable, get } from 'svelte/store';
import type { ChatMessage, Conversation } from '$lib/types';
import { messages } from '$lib/stores/chat';

import { nsForUser, keys, state } from '$lib/states/conversationState';

export const conversations = writable<Conversation[]>([]);
export const conversationMessages = writable<Record<string, ChatMessage[]>>({});
export const activeConversationId = writable<string | null>(null);

function buildTitleFromMessages(msgs: ChatMessage[]): string {
  const raw = msgs.map((m) => m.content).join(' ').replace(/\s+/g, ' ').trim();
  if (!raw) return 'Untitled';
  return raw.length <= 30 ? raw : raw.slice(0, 30) + '…';
}

// --- namespace (userless for now) ---
const ns = nsForUser(null);
const k = keys(ns);
let isHydratingMessages = false;

// --- hydrate on startup ---
function hydrateFromLocal() {
  const list = state.loadConversations(k.conversations);
  conversations.set(list);

  const active = state.loadActiveId(k.activeId);
  activeConversationId.set(active);

  // pre-load messages for active convo
  if (active) {
    const msgs = state.loadMessages(k.convMessages(active));
    messages.set(msgs);
  }
}
hydrateFromLocal();

// --- persist on change (with debounce) ---
let t1: any = null;
conversations.subscribe((list) => {
  clearTimeout(t1);
  t1 = setTimeout(() => state.saveConversations(k.conversations, list), 150);
});

let t2: any = null;
activeConversationId.subscribe((id) => {
  clearTimeout(t2);
  t2 = setTimeout(() => state.saveActiveId(k.activeId, id), 100);
});

// --- persist messages of the active conversation (with debounce) ---
let tM: any = null;
messages.subscribe((list) => {
  const active = get(activeConversationId);
  if (!active) return;

  // Skip when only opening/hydrating a convo
  if (isHydratingMessages) return;

  clearTimeout(tM);
  tM = setTimeout(() => {
    state.saveMessages(k.convMessages(active), list);

    // Only bump updatedAt when content actually changed by the user/assistant
    conversations.update((all) =>
      all
        .map((c) => (c.id === active ? { ...c, updatedAt: Date.now() } : c))
        .sort((a, b) => (b.updatedAt ?? 0) - (a.updatedAt ?? 0))
    );

    conversationMessages.update((map) => ({ ...map, [active]: list }));
  }, 120);
});
/**
 * Start a brand new chat (no active conversation; empty message list).
 * Does not save anything.
 * 
 * TODO: 
 * Change behaviour such that after first response a coversation is automatically 
 * saved to the conversation.
 * 
 * Only update convo updatedAt after user/assistant instead of each interaction
 */
export function startNewChat() {
  activeConversationId.set(null);
  messages.set([]);
}

/**
 * Save the current draft (only when no conversation is active),
 * then start a brand-new chat. If an active conversation is open,
 * do NOT duplicate it; simply start a new empty chat.
 *
 * Returns the saved conversation id (or null if nothing was saved).
 */
export function saveCurrentConversationAndStartNew(): string | null {
  const activeId = get(activeConversationId);
  const current = get(messages);

  // If an existing conversation is open, don't duplicate — just start fresh
  if (activeId !== null) {
    startNewChat();
    return null;
  }

  // New draft (no id yet)
  if (current.length === 0) {
    startNewChat();
    return null;
  }

  // Create a new conversation id + title
  const id = crypto.randomUUID();
  const title = buildTitleFromMessages(current);
  const now = Date.now();

  conversations.update((list) => [{ id, title, createdAt: now, updatedAt: now }, ...list]);

  // persist this conversation's messages to storage
  state.saveMessages(k.convMessages(id), current);

  // optional in-memory cache
  conversationMessages.update((map) => ({ ...map, [id]: current }));

  // clear to a new draft
  startNewChat();
  return id;
}

/**
 * Open an existing conversation into the chat area.
 */

export function openConversation(id: string) {
  activeConversationId.set(id);

  // Prevent the messages.subscribe side effects while we are just loading
  isHydratingMessages = true;
  try {
    const persisted = state.loadMessages(k.convMessages(id));
    messages.set(persisted);

    // optional in-memory cache
    conversationMessages.update((map) => ({ ...map, [id]: persisted }));
  } finally {
    // let Svelte flush, then re-enable (microtask/next tick pattern)
    queueMicrotask(() => (isHydratingMessages = false));
  }
}


export function renameConversation(id: string, newTitle: string) {
  const title = newTitle.trim();
  conversations.update((list) =>
    list.map((c) =>
      c.id === id
        ? { ...c, title: title.length ? title : 'Untitled' }
        : c
    )
  );
}

/**
 * Delete a conversation and clear it if it's currently active.
 */
export function deleteConversation(id: string) {
  conversations.update((list) => list.filter((c) => c.id !== id));
  conversationMessages.update((map) => {
    const next = { ...map };
    delete next[id];
    return next;
  });

  if (get(activeConversationId) === id) {
    startNewChat();
  }
}