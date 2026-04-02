let sessionTimer: ReturnType<typeof setTimeout> | null = null;
let inactivityTimer: ReturnType<typeof setTimeout> | null = null

const INACTIVITY_LIMIT = 15 * 60 * 1000; // 15 minutes

export function startInactivityWatcher() {
    resetInactivityTimer();

    // Listen to any user activity
    window.addEventListener('mousemove', resetInactivityTimer);
    window.addEventListener('keydown', resetInactivityTimer);
    window.addEventListener('click', resetInactivityTimer);
    window.addEventListener('scroll', resetInactivityTimer);
}

function resetInactivityTimer() {
    if (inactivityTimer) clearTimeout(inactivityTimer);

    inactivityTimer = setTimeout(() => {
        handleSessionExpired();
    }, INACTIVITY_LIMIT);
}


export function scheduleTokenExpiration(exp: number) {
    if (!exp) return;
    
    // Clear existing timers
    if (sessionTimer) clearTimeout(sessionTimer);

    // exp is in seconds → convert to ms
    const expiryMs = exp * 1000;
    const nowMs = Date.now();

    const delay = expiryMs - nowMs;

    if (delay <= 0) {
        handleSessionExpired();
        return;
    }

    // Schedule logout call
    sessionTimer = setTimeout(handleSessionExpired, delay);
}

async function handleSessionExpired() {

    await fetch('/api/logout', { method: 'POST' }).
    then(() => window.location.href = '/login?expired=1');
}