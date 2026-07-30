import { writable } from 'svelte/store';

export const scrollToBottomRequested = writable(0);

export function requestScrollToBottom() {
  scrollToBottomRequested.update((n) => n + 1);
}
