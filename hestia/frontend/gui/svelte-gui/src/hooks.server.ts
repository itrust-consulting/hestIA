import { redirect } from '@sveltejs/kit';

function isTokenExpired(token: string): boolean {
    try {
        const [, payloadB64] = token.split('.');
        const payloadJson = atob(payloadB64);
        const payload = JSON.parse(payloadJson);

        if (!payload.exp) return true;

        const nowSeconds = Math.floor(Date.now() / 1000);
        return payload.exp < nowSeconds;
    } catch {
        return true; // malformed token => treat as expired
    }
}

export const handle = async ({ event, resolve }) => {
    const token = event.cookies.get('token');

    const protectedRoutes = ['/chat', '/admin', '/account'];

    const isProtected = protectedRoutes.some(route =>
        event.url.pathname.startsWith(route)
    );

    if (isProtected) {

        // ✅ If no token → redirect
        if (!token) {
            throw redirect(302, '/login');
        }

        // ✅ If token exists but is expired → redirect & clear cookie
        if (isTokenExpired(token)) {
            event.cookies.delete('token', { path: '/' });
            throw redirect(302, '/login?expired=1');
        }
    }

    return resolve(event);
};