import { redirect } from '@sveltejs/kit';
import { isTokenExpired } from '$lib/auth/auth';

export function load({ cookies }) {
    const token = cookies.get('token');
    if (!token || isTokenExpired(token)) {
        throw redirect(302, '/login');
    }

    return {};
}