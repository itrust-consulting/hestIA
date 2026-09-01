import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, fetch }) => {
    if (!locals.user?.permissions?.is_admin) {
        error(403, 'Forbidden');
    }

    const res = await fetch('/api/admin/workflows');
    if (!res.ok) error(res.status, 'Failed to load workflows');
    const { workflows } = await res.json();

    return { workflows };
};
