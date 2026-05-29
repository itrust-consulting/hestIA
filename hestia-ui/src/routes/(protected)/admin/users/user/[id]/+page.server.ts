import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ fetch, params, locals }) => {
    if (!locals.user?.permissions?.is_admin) {
        error(403, 'Forbidden');
    }

    const [userRes, rolesRes, orgsRes] = await Promise.all([
        fetch(`/api/admin/users/user/${params.id}`),
        fetch('/api/admin/roles'),
        fetch('/api/admin/organizations'),
    ]);

    if (!userRes.ok) error(userRes.status as any, 'Failed to load user');

    const user = await userRes.json();
    const allRoles = rolesRes.ok ? (await rolesRes.json()) : [];
    const orgsData = orgsRes.ok ? (await orgsRes.json()) : { organizations: [] };

    return { user, allRoles, allOrgs: orgsData.organizations ?? [] };
};
