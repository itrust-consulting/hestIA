import { redirect } from '@sveltejs/kit';
import { env } from '$env/dynamic/public';
import { env as privateEnv } from '$env/dynamic/private';

const BACKEND_URL = privateEnv.PRIVATE_MICROSERVICE_URL || 'http://localhost:5555';

export async function GET({ cookies, url }) {
    cookies.delete('token', { path: '/', sameSite: 'lax', secure: true });

    if (env.PUBLIC_AUTH_MODE === 'oidc') {
        const postLogoutUri = `${url.origin}/login`;
        redirect(302, `${BACKEND_URL}/auth/oidc/logout?redirect_uri=${encodeURIComponent(postLogoutUri)}`);
    }

    redirect(302, '/login');
}
