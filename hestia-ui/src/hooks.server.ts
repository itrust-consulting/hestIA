import type { Handle } from '@sveltejs/kit';
import { backendFetch } from '$lib/server/backend';

export const handle: Handle = async ({ event, resolve }) => {
    const token = event.cookies.get('token');

    event.locals.user = null;

    if (token) {
        try {
            const upstream = await backendFetch('/account', token);

            if (upstream.ok) {
                event.locals.user = await upstream.json();
            } else {
                event.cookies.delete('token', { path: '/' });
            }
        } catch (err) {
            console.error('Failed to fetch user profile', err);
        }
    }

    // Redirect legacy /mod/* URLs to /admin/*
    if (event.url.pathname.startsWith('/mod/') || event.url.pathname === '/mod') {
        const newPath = event.url.pathname.replace(/^\/mod/, '/admin');
        return Response.redirect(new URL(newPath + event.url.search, event.url.origin), 301);
    }

    // Guard all /api/admin/* routes — require admin or moderator role.
    // Fine-grained authorization is enforced by the backend; this is defense-in-depth.
    if (event.url.pathname.startsWith('/api/admin/')) {
        const perms = event.locals.user?.permissions;
        const isAdmin = perms?.is_admin ?? false;
        const isModerator = (perms?.moderated_tenants?.length ?? 0) > 0;
        if (!isAdmin && !isModerator) {
            return new Response('Forbidden', { status: 403 });
        }
    }

    return resolve(event);
};