import { goto } from '$app/navigation';
import { clearIsmsState } from '$lib/stores/isms';
import { unreadCount } from '$lib/stores/notifications';

let sessionTimer: ReturnType<typeof setTimeout> | null = null;
let inactivityTimer: ReturnType<typeof setTimeout> | null = null;
let inactivityLimitMs = 30 * 60 * 1000; // default 30 min; overridden by scheduleTokenExpiration

let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
// Short enough that a new/updated unread count feels immediate on the bell
// icon without requiring a click, a tab switch, or a reload -- this same
// call also drives the admin online/offline status, so there's no separate
// mechanism to keep in sync.
const HEARTBEAT_INTERVAL_MS = 5 * 1000;

// Pings the backend every ~5s while the app is open, independent of
// mouse/keyboard activity -- unlike the inactivity watcher above, this is
// meant to keep signaling "the tab is open" even when idle, so admin User
// management can show a real online/offline status, and so the unread
// notification badge stays current.
export function startHeartbeat() {
    if (heartbeatTimer) return;
    sendHeartbeat();
    heartbeatTimer = setInterval(sendHeartbeat, HEARTBEAT_INTERVAL_MS);

    // Background tabs get their setInterval calls throttled by the browser
    // (often to well over a minute), so switching away to e.g. create a user
    // or send a broadcast elsewhere and back can leave the unread badge
    // stale far longer than HEARTBEAT_INTERVAL_MS would suggest. Firing one
    // immediately on refocus keeps it current without waiting on the timer.
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible') sendHeartbeat();
    });
}

export async function sendHeartbeat() {
    try {
        const res = await fetch('/api/account/heartbeat', { method: 'POST' });
        if (res.ok) {
            const data = await res.json();
            if (typeof data.unread_notifications === 'number') {
                unreadCount.set(data.unread_notifications);
            }
        }
    } catch {
        // best-effort — a missed beat just means one skipped last_seen update
    }
}

export function startInactivityWatcher() {
    resetInactivityTimer();

    window.addEventListener('mousemove', resetInactivityTimer);
    window.addEventListener('keydown', resetInactivityTimer);
    window.addEventListener('click', resetInactivityTimer);
    window.addEventListener('scroll', resetInactivityTimer);
}

function resetInactivityTimer() {
    if (inactivityTimer) clearTimeout(inactivityTimer);
    inactivityTimer = setTimeout(handleSessionExpired, inactivityLimitMs);
}


export function scheduleTokenExpiration(exp: number) {
    if (!exp) return;

    if (sessionTimer) clearTimeout(sessionTimer);

    const delay = exp * 1000 - Date.now();

    if (delay <= 0) {
        handleSessionExpired();
        return;
    }

    inactivityLimitMs = delay / 2;
    resetInactivityTimer();

    sessionTimer = setTimeout(handleSessionExpired, delay);
}

async function handleSessionExpired() {
    clearIsmsState();
    window.location.href = '/api/logout';
}