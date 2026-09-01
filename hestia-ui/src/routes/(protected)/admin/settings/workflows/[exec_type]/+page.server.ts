import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, fetch, params }) => {
    if (!locals.user?.permissions?.is_admin) {
        error(403, 'Forbidden');
    }

    const res = await fetch('/api/admin/workflows');
    if (!res.ok) error(res.status, 'Failed to load workflows');
    const { workflows } = await res.json();

    const workflow = workflows.find((w: { exec_type: string }) => w.exec_type === params.exec_type);
    if (!workflow) error(404, 'Unknown workflow');

    return { workflow };
};
