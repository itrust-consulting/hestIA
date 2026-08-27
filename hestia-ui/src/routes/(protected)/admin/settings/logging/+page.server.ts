import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, fetch }) => {
    if (!locals.user?.permissions?.is_admin) {
        error(403, 'Forbidden');
    }

    const settingsRes = await fetch('/api/admin/logs/settings');
    if (!settingsRes.ok) error(settingsRes.status, 'Failed to load logging settings');

    return {
        logSettings: await settingsRes.json(),
    };
};
