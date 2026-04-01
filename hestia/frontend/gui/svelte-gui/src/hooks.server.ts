// src/hooks.server.ts
import { redirect } from '@sveltejs/kit';

export const handle = async ({ event, resolve }) => {
    const token = event.cookies.get('token');


    const protectedRoutes = [
        '/chat',
        '/admin',
        '/account',
    ];

    const isProtected = protectedRoutes.some((route) =>
        event.url.pathname.startsWith(route)
    );

    if (isProtected && !token) {
        // redirect to login if not logged in
        throw redirect(302, '/login');
    }

    return resolve(event);
};