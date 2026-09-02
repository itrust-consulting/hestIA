import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, fetch }) => {
    if (!locals.user?.permissions?.is_admin) {
        error(403, 'Forbidden');
    }

    const [settingsRes, historyRes] = await Promise.all([
        fetch('/api/admin/notification-settings'),
        fetch('/api/admin/notifications/history'),
    ]);
    if (!settingsRes.ok) error(settingsRes.status, 'Failed to load notification settings');

    const history = historyRes.ok ? await historyRes.json() : { broadcasts: [] };

    return {
        welcomeSettings: await settingsRes.json(),
        broadcasts: history.broadcasts ?? [],
    };
};
