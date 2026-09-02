import { writable } from 'svelte/store';
import type { Notification } from '$lib/types';

export const unreadCount = writable<number>(0);
export const notifications = writable<Notification[]>([]);
export const notificationsLoading = writable<boolean>(false);

export async function fetchNotifications(): Promise<void> {
  notificationsLoading.set(true);
  try {
    const res = await fetch('/api/notifications');
    if (!res.ok) return;
    const data = await res.json();
    const list: Notification[] = data.notifications ?? [];
    notifications.set(list);
    // Derive the badge count from this same response instead of relying on
    // a separate heartbeat round-trip -- this is the exact data the dropdown
    // list renders, so the badge can never disagree with what's visible.
    unreadCount.set(list.filter(n => !n.is_read).length);
  } finally {
    notificationsLoading.set(false);
  }
}

export async function markRead(id: string): Promise<void> {
  notifications.update(list => list.map(n => (n.id === id ? { ...n, is_read: true } : n)));
  unreadCount.update(n => Math.max(0, n - 1));
  try {
    await fetch(`/api/notifications/${id}/read`, { method: 'POST' });
  } catch {
    // best-effort — next fetch/heartbeat will reconcile
  }
}

export async function markAllRead(): Promise<void> {
  notifications.update(list => list.map(n => ({ ...n, is_read: true })));
  unreadCount.set(0);
  try {
    await fetch('/api/notifications/read-all', { method: 'POST' });
  } catch {
    // best-effort — next fetch/heartbeat will reconcile
  }
}
