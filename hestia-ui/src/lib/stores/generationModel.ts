import { writable } from 'svelte/store';

export const activeModel = writable<string | null>(null);

export async function loadActiveModel() {
  const res = await fetch('/api/chat/model');
  if (!res.ok) return;
  const data: { model: string | null } = await res.json();
  activeModel.set(data.model);
}
