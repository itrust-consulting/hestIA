import { redirect } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

const API_URL = env.PRIVATE_MICROSERVICE_URL || 'http://localhost:5555';

export async function GET({ url, cookies }) {
    const callbackUrl = `${url.origin}/api/auth/callback`;

    let authUrl: string;
    let state: string;
    let codeVerifier: string | undefined;

    try {
        const res = await fetch(
            `${API_URL}/auth/oidc/authorize?redirect_uri=${encodeURIComponent(callbackUrl)}`
        );
        if (!res.ok) throw new Error(`Backend returned ${res.status}`);
        ({ url: authUrl, state, code_verifier: codeVerifier } = await res.json());
    } catch {
        redirect(302, '/login?error=oidc_unavailable');
    }

    cookies.set('oidc_state', state!, {
        httpOnly: true,
        secure: url.protocol === 'https:',
        sameSite: 'lax',
        path: '/',
        maxAge: 60 * 5
    });

    if (codeVerifier) {
        cookies.set('oidc_verifier', codeVerifier, {
            httpOnly: true,
            secure: url.protocol === 'https:',
            sameSite: 'lax',
            path: '/',
            maxAge: 60 * 5
        });
    }

    redirect(302, authUrl!);
}
