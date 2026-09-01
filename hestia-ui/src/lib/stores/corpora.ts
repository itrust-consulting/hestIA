import { writable } from 'svelte/store';
import type { CollectionPermission, User } from '$lib/types';

export type Collection = { id: string; name: string };

export const corpora = writable<Collection[]>([]);
export const corporaLoaded = writable(false);

/** Shared by the "Ask My Docs" picker modal and the corpus-cycling
 *  keyboard shortcut, so both see the same list without double-fetching. */
export async function loadCorpora(user: User | undefined | null) {
  corporaLoaded.set(false);

  const allowed = user?.permissions?.allowed_collections;

  if (!allowed) {
    corpora.set([]);
    corporaLoaded.set(true);
    return;
  }

  // Admin: fetch all collections from backend
  if (user?.permissions?.is_admin === true) {
    const res = await fetch('/api/collections');
    const data: { collections: Collection[] } = await res.json();
    corpora.set(data.collections);
  } else {
    // Regular users: only those with access === true
    corpora.set(
      Object.entries(allowed)
        .filter(([, v]: [string, CollectionPermission]) => v.access === true)
        .map(([id]) => ({ id, name: id }))
    );
  }

  corporaLoaded.set(true);
}
