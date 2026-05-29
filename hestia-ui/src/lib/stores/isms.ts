import { writable } from 'svelte/store';
import { browser } from '$app/environment';

// ---- namespacing (swap userId when you add auth) ----
const ns = 'hestia:guest:isms'; // later: `hestia:user:${userId}:isms`

const K = {
  corpusId: `${ns}:activeCorpusId`,
  corpusName: `${ns}:activeCorpusName`,
  active: `${ns}:isIsmsActive`
};

// ---- load helpers ----
function loadString(key: string): string | null {
  if (!browser) return null;
  try {
    const v = localStorage.getItem(key);
    return v === null ? null : v;
  } catch {
    return null;
  }
}

function loadBool(key: string, fallback = false): boolean {
  if (!browser) return fallback;
  try {
    const v = localStorage.getItem(key);
    if (v === null) return fallback;
    return v === 'true';
  } catch {
    return fallback;
  }
}

// ---- initial state from storage (client only) ----
const initialCorpusId = loadString(K.corpusId);
const initialCorpusName = loadString(K.corpusName);
const initialActive = loadBool(K.active, false);

// ---- stores ----
export const activeCorpusId = writable<string | null>(initialCorpusId);
export const activeCorpusName = writable<string | null>(initialCorpusName);
export const isIsmsActive = writable<boolean>(initialActive);

// ---- persist on change (client only) ----
if (browser) {
  activeCorpusId.subscribe((v) => {
    try {
      if (v === null) localStorage.removeItem(K.corpusId);
      else localStorage.setItem(K.corpusId, v);
    } catch {}
  });

  activeCorpusName.subscribe((v) => {
    try {
      if (v === null) localStorage.removeItem(K.corpusName);
      else localStorage.setItem(K.corpusName, v);
    } catch {}
  });

  isIsmsActive.subscribe((v) => {
    try {
      localStorage.setItem(K.active, String(v));
    } catch {}
  });
}

// ---- optional helpers ----
export function clearIsmsState() {
  // Call this on logout or when switching organizations
  activeCorpusId.set(null);
  activeCorpusName.set(null);
  isIsmsActive.set(false);

  if (browser) {
    localStorage.removeItem(K.corpusId);
    localStorage.removeItem(K.corpusName);
    localStorage.removeItem(K.active);
  }
}