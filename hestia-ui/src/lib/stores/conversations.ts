import { writable, get } from 'svelte/store';
import { tick } from 'svelte';
import { browser } from '$app/environment';
import { replaceState } from '$app/navigation';

import type { Conversation } from '$lib/types';
import { messages, isMutatingFront } from '$lib/stores/chat';
import { requestScrollToBottom } from '$lib/stores/chatScroll';
import { api } from '$lib/api/client';
import { contextBudget, setContextBudget } from '$lib/stores/contextBudget';

const PAGE_SIZE = 20;
// Always keep at least this many loaded messages above the current viewport
// as a scroll-ahead buffer, so a small scroll-up never needs a fetch.
const KEEP_BUFFER = PAGE_SIZE;
// How long a chunk of history has to sit unviewed (scrolled away from, below
// the keep buffer) before it's evicted from memory.
const STALE_GRACE_MS = 15_000;

function parseDocumentBlocks(content: string): Map<string, string> {
  const result = new Map<string, string>();
  const regex = /<document name="([^"]+)">\n([\s\S]*?)\n<\/document>/g;
  let match;
  while ((match = regex.exec(content)) !== null) {
    result.set(match[1], match[2]);
  }
  return result;
}

function mapRawMessages(raw: any[]) {
  return raw.map(rawMsg => {
    // The server returns snake_case `created_at`; normalize to `createdAt` so
    // fetched messages match the field live-pushed messages already use
    // (pushMessage/sendMessage set `createdAt` directly) — every ChatMessage
    // must have a consistent `createdAt` for sliding-window cursor bookkeeping.
    const { created_at, ...m } = rawMsg;
    const createdAt = created_at ?? m.createdAt;
    const meta = typeof m.metadata === 'string' ? JSON.parse(m.metadata) : (m.metadata ?? {});
    if (m.role === 'user' && meta.display_content !== undefined) {
      const docBlocks = parseDocumentBlocks(m.content);
      const attachments = (meta.attachments ?? []).map((a: { name: string; size?: number }) => ({
        ...a,
        markdown: docBlocks.get(a.name),
      }));
      return { ...m, createdAt, apiContent: m.content, content: meta.display_content, attachments };
    }
    if (m.role === 'assistant' && (meta.citations?.length || meta.thinking)) {
      return { ...m, createdAt, citations: meta.citations, thinking: meta.thinking };
    }
    return { ...m, createdAt };
  });
}

type Cursor = { created_at: number; rowid: number } | null;

export const conversations = writable<Conversation[]>([]);
export const activeConversationId = writable<string | null>(null);
export const isLoadingMessages = writable<boolean>(false);
export const hasMoreBefore = writable<boolean>(false);
export const isLoadingOlder = writable<boolean>(false);

// Cursor to fetch the next page of OLDER messages (null = nothing older left, or unknown yet)
let beforeCursor: Cursor = null;

// How many messages at the front of the array are currently scrolled far
// enough above the viewport to be considered abandoned, and since when.
// Reset whenever the user scrolls back up into that range.
let staleHeadCount = 0;
let staleSince: number | null = null;

/** Called on every scroll with the index of the topmost visible message.
 *  Tracks how much history above the keep buffer has been scrolled away
 *  from, and evicts it once it's been stale for STALE_GRACE_MS. */
export function reportScrollPosition(topVisibleIndex: number) {
  const stale = Math.max(0, topVisibleIndex - KEEP_BUFFER);
  if (stale <= 0) {
    staleHeadCount = 0;
    staleSince = null;
    return;
  }
  if (staleSince === null) {
    staleHeadCount = stale;
    staleSince = Date.now();
    return;
  }
  staleHeadCount = stale;
  if (Date.now() - staleSince >= STALE_GRACE_MS) {
    evictStaleHead();
  }
}

/** Evict whatever's currently marked stale right away, bypassing the grace
 *  period — meant to be called when a new request is about to fire (sending
 *  a message), so we don't hang on to abandoned history indefinitely. */
export function forceEvictStaleHeadNow() {
  if (staleHeadCount > 0) evictStaleHead();
}

async function evictStaleHead() {
  const current = get(messages);
  const evictCount = Math.min(staleHeadCount, current.length);
  staleHeadCount = 0;
  staleSince = null;
  if (evictCount <= 0) return;

  const evictedBoundary = current[evictCount - 1];
  const remaining = current.slice(evictCount);

  // live (not-yet-persisted) messages are always at the tail, so the head is
  // always server-fetched and has a rowid whenever eviction is possible at all
  if (evictedBoundary.rowid != null) {
    beforeCursor = { created_at: evictedBoundary.createdAt, rowid: evictedBoundary.rowid };
    hasMoreBefore.set(true);
  }

  isMutatingFront.set(true);
  messages.set(remaining);
  await tick();
  isMutatingFront.set(false);
}

export async function loadConversations() {
  const res = await api.get('/api/conversations');
  if (!res.ok) throw new Error('Failed to load conversations');
  const data: Conversation[] = await res.json();
  conversations.set(data);
}

export async function openConversation(id: string) {
  activeConversationId.set(id);
  if (browser) replaceState(`/chat?cid=${id}`, {});
  beforeCursor = null;
  hasMoreBefore.set(false);
  staleHeadCount = 0;
  staleSince = null;

  isLoadingMessages.set(true);
  const res = await api.get(`/api/conversations/${id}?limit=${PAGE_SIZE}`);
  if (!res.ok) throw new Error('Failed to load messages');

  const { messages: raw, has_more, next_cursor, used_tokens, max_tokens, needs_compaction } = await res.json();
  messages.set(mapRawMessages(raw));
  hasMoreBefore.set(has_more);
  beforeCursor = next_cursor;
  isLoadingMessages.set(false);
  setContextBudget(used_tokens, max_tokens, needs_compaction);

  requestScrollToBottom();
}

export async function loadOlderMessages() {
  const id = get(activeConversationId);
  if (!id || !beforeCursor || get(isLoadingOlder)) return;

  isLoadingOlder.set(true);
  try {
    const qs = new URLSearchParams({
      limit: String(PAGE_SIZE),
      before_created_at: String(beforeCursor.created_at),
      before_rowid: String(beforeCursor.rowid),
    });
    const res = await api.get(`/api/conversations/${id}?${qs}`);
    if (!res.ok) throw new Error('Failed to load older messages');
    const { messages: raw, has_more, next_cursor } = await res.json();
    const older = mapRawMessages(raw);

    isMutatingFront.set(true);
    messages.set([...older, ...get(messages)]);
    // keep shift-mode active on <VList> through the render that processes this
    // length change, then release it so later appends (new messages, streaming)
    // aren't mistaken for a prepend
    await tick();
    isMutatingFront.set(false);
    hasMoreBefore.set(has_more);
    beforeCursor = next_cursor;
  } finally {
    isLoadingOlder.set(false);
  }
}

export function startNewChat() {
  activeConversationId.set(null);
  messages.set([]);
  beforeCursor = null;
  hasMoreBefore.set(false);
  staleHeadCount = 0;
  staleSince = null;
  contextBudget.set(null);
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
