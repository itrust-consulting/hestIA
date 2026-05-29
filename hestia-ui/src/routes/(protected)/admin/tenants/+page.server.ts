import { error } from '@sveltejs/kit';
import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, fetch }) => {
    const perms = locals.user?.permissions;
    const isAdmin = perms?.is_admin ?? false;
    const moderated_tenants: number[] = perms?.moderated_tenants ?? [];

    if (isAdmin) {
        const res = await fetch('/api/admin/tenants');
        if (!res.ok) error(res.status as any, 'Failed to load tenants');
        const data = await res.json();
        return { tenants: (data.organizations ?? []) as { id: number; name: string; abbreviation: string; created_at: number; member_count?: number }[] };
    }

    // For moderators: only fetch their moderated tenants. Resolve member counts via the
    // per-tenant members endpoint, which is guarded server-side (require_tenant_moderator),
    // so no client-side filtering is needed and no other tenant's data is exposed.
    const orgs = (locals.user?.orgs ?? []) as { id: number; name: string; abbr: string; created_at: number }[];
    const myOrgs = orgs.filter(o => moderated_tenants.includes(o.id));
    const tenants = await Promise.all(
        myOrgs.map(async o => {
            const membersRes = await fetch(`/api/admin/tenants/${o.id}/members`);
            const memberCount = membersRes.ok
                ? ((await membersRes.json()).members ?? []).length
                : undefined;
            return { id: o.id, name: o.name, abbreviation: o.abbr, created_at: o.created_at, member_count: memberCount };
        })
    );
    return { tenants };
};
