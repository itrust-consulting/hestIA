import type { LayoutServerLoad } from './$types';
import { jwtDecode } from 'jwt-decode';

export const load: LayoutServerLoad = ({ locals, cookies }) => {
    let tokenExp: number | null = null;
    const token = cookies.get('token');

    if (token) {
        try {
            const decoded: any = jwtDecode(token);
            tokenExp = decoded.exp ?? null;
        } catch {}
    }

    return {
        user: locals.user,
        tokenExp
    };
};