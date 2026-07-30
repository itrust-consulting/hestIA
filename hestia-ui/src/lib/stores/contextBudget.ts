import { writable, get } from 'svelte/store';
import { api } from '$lib/api/client';

export type ContextBudget = {
  usedTokens: number;
  maxTokens: number;
  needsCompaction: boolean;
} | null;

export const contextBudget = writable<ContextBudget>(null);
export const compacting = writable<boolean>(false);

export function setContextBudget(
  usedTokens: number | null | undefined,
  maxTokens: number | null | undefined,
  needsCompaction: boolean | null | undefined
) {
  if (usedTokens == null || maxTokens == null) return;
  contextBudget.set({ usedTokens, maxTokens, needsCompaction: !!needsCompaction });
}

export async function compactNow(conversationId: string): Promise<'compacted' | 'not_needed' | null> {
  if (get(compacting)) return null;
  compacting.set(true);
  try {
    const res = await api.post(`/api/conversations/${conversationId}/compact`, {});
    if (!res.ok) return null;
    const { status, used_tokens, max_tokens } = await res.json();
    setContextBudget(used_tokens, max_tokens, false);
    return status;
  } finally {
    compacting.set(false);
  }
}
