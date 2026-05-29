import { error } from '@sveltejs/kit';

export function load({ locals }) {
    const perms = locals.user?.permissions;
    const isAdmin = perms?.is_admin ?? false;
    const moderated_tenants: number[] = perms?.moderated_tenants ?? [];

    if (!isAdmin && moderated_tenants.length === 0) {
        error(403, 'Forbidden');
    }

    return {
        isAdmin,
        moderated_tenants,
        user_orgs: (locals.user?.orgs ?? []) as { id: number; name: string; abbr: string; created_at: number }[],
    };
}
