import { redirect } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';
import { backendFetch } from '$lib/server/backend';

const BACKEND_URL = env.PRIVATE_MICROSERVICE_URL || 'http://localhost:5555';

export async function GET({ cookies, url, locals }) {
    const isOidcUser = locals.user?.auth_source === 'oidc';

    // Audit the logout while the token is still valid -- best-effort, a
    // backend hiccup here shouldn't block the user from actually logging out.
    try {
        await backendFetch('/logout', cookies.get('token'), { method: 'POST' });
    } catch {
        // backend unreachable — fall through, still log the user out locally
    }

    cookies.delete('token', { path: '/', sameSite: 'lax', secure: url.protocol === 'https:' });

    if (isOidcUser) {
        const postLogoutUri = `${url.origin}/login`;
        try {
            const backendRes = await fetch(
                `${BACKEND_URL}/auth/oidc/logout?redirect_uri=${encodeURIComponent(postLogoutUri)}`,
                { redirect: 'manual' },
            );
            const oidcLogoutUrl = backendRes.headers.get('location');
            if (oidcLogoutUrl) redirect(302, oidcLogoutUrl);
        } catch {
            // backend unreachable — fall through to local redirect
        }
    }

    redirect(302, '/login');
}
