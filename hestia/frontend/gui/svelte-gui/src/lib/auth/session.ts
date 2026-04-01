// src/lib/auth/session.ts
import { goto } from '$app/navigation';

let sessionTimer: ReturnType<typeof setTimeout> | null = null;

function decodeJwt(token: string): any {
    // Decode base64 payload only
    const payload = token.split('.')[1];
    try {
        return JSON.parse(atob(payload));
    } catch {
        return null;
    }
}

export function scheduleTokenExpiryWatcher(token: string) {
    if (!token) return;

    // Clear existing timers
    if (sessionTimer) clearTimeout(sessionTimer);

    const decoded = decodeJwt(token);
    if (!decoded || !decoded.exp) return; // no exp claim → do nothing

    // exp is in seconds → convert to ms
    const expiryMs = decoded.exp * 1000;
    const nowMs = Date.now();

    const delay = expiryMs - nowMs;

    if (delay <= 0) {
        handleSessionExpired();
        return;
    }

    // Schedule logout call
    sessionTimer = setTimeout(handleSessionExpired, delay);
}

function handleSessionExpired() {
    // Clear token cookie (client‑side)
    document.cookie = "token=; Path=/; Max-Age=0";

    // Optional UI feedback
    alert("Your session has expired. Please log in again.");

    goto('/login');
}