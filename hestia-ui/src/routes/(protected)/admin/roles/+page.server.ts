import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, fetch }) => {
    if (!locals.user?.permissions?.is_admin) {
        error(403, 'Forbidden');
    }

    const res = await fetch('/api/admin/roles');
    if (!res.ok) error(res.status as any, 'Failed to load roles');
    const roles = await res.json();

    return { roles };
};
