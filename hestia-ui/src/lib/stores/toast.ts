import { writable } from 'svelte/store';

export type ToastType = 'success' | 'error' | 'info';

export type ActionToast = {
  id: string;
  message: string;
  type: ToastType;
};

export const actionToasts = writable<ActionToast[]>([]);

export function addToast(message: string, type: ToastType = 'info', duration?: number): void {
  const id = crypto.randomUUID();
  const ms = duration ?? (type === 'error' ? 6000 : 3000);
  actionToasts.update(ts => [...ts, { id, message, type }]);
  setTimeout(() => actionToasts.update(ts => ts.filter(t => t.id !== id)), ms);
}
