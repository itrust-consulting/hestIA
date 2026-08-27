import { goto } from '$app/navigation';
import { clearIsmsState } from '$lib/stores/isms';

let sessionTimer: ReturnType<typeof setTimeout> | null = null;
let inactivityTimer: ReturnType<typeof setTimeout> | null = null;
let inactivityLimitMs = 30 * 60 * 1000; // default 30 min; overridden by scheduleTokenExpiration

let heartbeatTimer: ReturnType<typeof setInterval> | null = null;
const HEARTBEAT_INTERVAL_MS = 45 * 1000;

// Pings the backend every ~45s while the app is open, independent of
// mouse/keyboard activity -- unlike the inactivity watcher above, this is
// meant to keep signaling "the tab is open" even when idle, so admin User
// management can show a real online/offline status.
export function startHeartbeat() {
    if (heartbeatTimer) return;
    sendHeartbeat();
    heartbeatTimer = setInterval(sendHeartbeat, HEARTBEAT_INTERVAL_MS);
}

async function sendHeartbeat() {
    try {
        await fetch('/api/account/heartbeat', { method: 'POST' });
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