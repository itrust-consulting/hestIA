import { writable, derived, get } from 'svelte/store';
import { browser } from '$app/environment';

// ---- namespacing (swap userId when you add auth) ----
const ns = 'hestia:guest:isms'; // later: `hestia:user:${userId}:isms`
const STORAGE_KEY = `${ns}:byConversation`;

// Key used for the corpus selection of a chat that hasn't been sent yet
// (activeConversationId is still null, so there's no real id to key on).
const NEW_CHAT_KEY = '__new__';

type Selection = { corpusId: string | null; corpusName: string | null; active: boolean };
const EMPTY: Selection = { corpusId: null, corpusName: null, active: false };

function loadMap(): Record<string, Selection> {
  if (!browser) return {};
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : {};
  } catch {
    return {};
  }
}

// ---- per-conversation selection store ----
const byConversation = writable<Record<string, Selection>>(loadMap());

if (browser) {
  byConversation.subscribe((map) => {
    try {
      // Never persist the in-progress "new chat" draft -- a selection tied
      // to a not-yet-created conversation is meaningless after a reload.
      const { [NEW_CHAT_KEY]: _draft, ...persisted } = map;
      localStorage.setItem(STORAGE_KEY, JSON.stringify(persisted));
    } catch {}
  });
}

// Which conversation's selection is "live" right now. Kept in sync
// externally by conversations.ts (openConversation/startNewChat) and
// actions.ts (once a new chat gets its real id) -- this module has no
// notion of "the active conversation" on its own.
const currentKey = writable<string>(NEW_CHAT_KEY);

export function setActiveConversation(id: string | null) {
  currentKey.set(id ?? NEW_CHAT_KEY);
}

// ---- read-only stores mirroring the active conversation's selection ----
export const activeCorpusId = derived(
  [byConversation, currentKey],
  ([$map, $key]) => ($map[$key] ?? EMPTY).corpusId
);
export const activeCorpusName = derived(
  [byConversation, currentKey],
  ([$map, $key]) => ($map[$key] ?? EMPTY).corpusName
);
export const isIsmsActive = derived(
  [byConversation, currentKey],
  ([$map, $key]) => ($map[$key] ?? EMPTY).active
);

// ---- mutators, always acting on whichever conversation is currently active ----
export function selectCorpus(corpusId: string, corpusName: string | null) {
  const key = get(currentKey);
  byConversation.update((map) => ({ ...map, [key]: { corpusId, corpusName, active: true } }));
}

export function deactivateCorpus() {
  const key = get(currentKey);
  byConversation.update((map) => ({ ...map, [key]: { ...EMPTY } }));
}

/** Flip RAG on/off for the active conversation without losing the chosen
 *  corpus. Returns false if no corpus has ever been picked for this
 *  conversation, so the caller can open the picker instead. */
export function toggleIsmsActive(): boolean {
  const key = get(currentKey);
  const current = get(byConversation)[key] ?? EMPTY;
  if (!current.corpusId) return false;
  byConversation.update((map) => ({ ...map, [key]: { ...current, active: !current.active } }));
  return true;
}

/** Called when a brand-new chat is started: the draft selection always
 *  starts blank rather than carrying over the previous conversation's. */
export function resetNewChatSelection() {
  currentKey.set(NEW_CHAT_KEY);
  byConversation.update((map) => {
    const { [NEW_CHAT_KEY]: _draft, ...rest } = map;
    return rest;
  });
}

/** Called once the backend assigns a real id to what was being composed as
 *  a new chat, so a corpus picked before the first message is sent carries
 *  over to the now-persisted conversation instead of being lost. */
export function migrateNewChatSelection(newId: string) {
  if (get(currentKey) !== NEW_CHAT_KEY) return;
  byConversation.update((map) => {
    const draft = map[NEW_CHAT_KEY];
    const { [NEW_CHAT_KEY]: _draft, ...rest } = map;
    return draft ? { ...rest, [newId]: draft } : rest;
  });
  currentKey.set(newId);
}

export function removeConversationSelection(id: string) {
  byConversation.update((map) => {
    if (!(id in map)) return map;
    const { [id]: _removed, ...rest } = map;
    return rest;
  });
}

// ---- cross-component "open the corpus picker" signal, mirrors
// chatScroll.ts's scrollToBottomRequested pattern ----
export const ismsModalOpenRequested = writable(0);
export function requestOpenIsmsModal() {
  ismsModalOpenRequested.update((n) => n + 1);
}

// ---- optional helpers ----
export function clearIsmsState() {
  // Call this on logout or when switching organizations
  byConversation.set({});
  currentKey.set(NEW_CHAT_KEY);
}
