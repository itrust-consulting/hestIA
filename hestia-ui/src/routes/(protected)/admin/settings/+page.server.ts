import { error } from '@sveltejs/kit';

export function load({ locals }) {
    if (!locals.user?.permissions?.is_admin) {
        error(403, 'Forbidden');
    }

    return {};
}
