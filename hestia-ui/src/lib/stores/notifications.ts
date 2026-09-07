import { writable } from 'svelte/store';
import type { Notification } from '$lib/types';

type NotificationCursor = { created_at: number; rowid: number };

export const unreadCount = writable<number>(0);
export const notifications = writable<Notification[]>([]);
export const notificationsLoading = writable<boolean>(false);
export const hasMoreNotifications = writable<boolean>(false);
export const isLoadingMoreNotifications = writable<boolean>(false);

// The backend already supports cursor pagination here (before_created_at /
// before_rowid, mirroring conversations.ts's history pager) -- it just
// wasn't wired up on this side, so anyone with more than one page of
// notifications could never see the older ones.
let beforeCursor: NotificationCursor | null = null;

export async function fetchNotifications(): Promise<void> {
  notificationsLoading.set(true);
  try {
    const res = await fetch('/api/notifications');
    if (!res.ok) return;
    const data = await res.json();
    const list: Notification[] = data.notifications ?? [];
    notifications.set(list);
    hasMoreNotifications.set(Boolean(data.has_more));
    beforeCursor = data.next_cursor ?? null;
    // Derive the badge count from this same response instead of relying on
    // a separate heartbeat round-trip -- this is the exact data the dropdown
    // list renders, so the badge can never disagree with what's visible.
    unreadCount.set(list.filter(n => !n.is_read).length);
  } finally {
    notificationsLoading.set(false);
  }
}

export async function loadMoreNotifications(): Promise<void> {
  if (!beforeCursor) return;
  isLoadingMoreNotifications.set(true);
  try {
    const qs = new URLSearchParams({
      before_created_at: String(beforeCursor.created_at),
      before_rowid: String(beforeCursor.rowid)
    });
    const res = await fetch(`/api/notifications?${qs}`);
    if (!res.ok) return;
    const data = await res.json();
    const older: Notification[] = data.notifications ?? [];
    notifications.update(list => [...list, ...older]);
    hasMoreNotifications.set(Boolean(data.has_more));
    beforeCursor = data.next_cursor ?? null;
  } finally {
    isLoadingMoreNotifications.set(false);
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
