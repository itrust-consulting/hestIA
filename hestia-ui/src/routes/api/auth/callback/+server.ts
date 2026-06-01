import { redirect } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';
import { jwtDecode } from 'jwt-decode';

const API_URL = env.PRIVATE_MICROSERVICE_URL || 'http://localhost:5555';

export async function GET({ url, cookies }) {
    const code = url.searchParams.get('code');
    const state = url.searchParams.get('state');
    const storedState = cookies.get('oidc_state');

    cookies.delete('oidc_state', { path: '/' });

    if (!code) {
        redirect(302, '/login?error=oidc_no_code');
    }

    if (!storedState || state !== storedState) {
        redirect(302, '/login?error=oidc_state_mismatch');
    }

    const callbackUrl = `${url.origin}/api/auth/callback`;

    let data: { access_token: string; must_change_pw: boolean };

    try {
        const res = await fetch(`${API_URL}/auth/oidc/callback`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code, redirect_uri: callbackUrl, state })
        });
        if (!res.ok) throw new Error(`Backend returned ${res.status}`);
        data = await res.json();
    } catch {
        redirect(302, '/login?error=oidc_exchange_failed');
    }

    const decoded: any = jwtDecode(data!.access_token);
    const exp: number = decoded.exp;

    cookies.set('token', data!.access_token, {
        httpOnly: true,
        secure: url.protocol === 'https:',
        sameSite: 'lax',
        path: '/',
        maxAge: exp - Math.floor(Date.now() / 1000)
    });

    if (data!.must_change_pw) {
        redirect(302, '/account/overview?section=security');
    }

    redirect(302, '/chat');
}
