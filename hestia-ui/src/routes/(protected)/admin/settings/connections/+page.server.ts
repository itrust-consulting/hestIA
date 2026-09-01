import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, fetch }) => {
    if (!locals.user?.permissions?.is_admin) {
        error(403, 'Forbidden');
    }

    const connRes = await fetch('/api/admin/llm-connections');
    if (!connRes.ok) error(connRes.status, 'Failed to load LLM connections');

    return {
        connections: (await connRes.json()).connections ?? [],
    };
};
