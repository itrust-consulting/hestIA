import { goto } from '$app/navigation';
import { clearIsmsState } from '$lib/stores/isms';

let sessionTimer: ReturnType<typeof setTimeout> | null = null;
let inactivityTimer: ReturnType<typeof setTimeout> | null = null;
let inactivityLimitMs = 30 * 60 * 1000; // default 30 min; overridden by scheduleTokenExpiration

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