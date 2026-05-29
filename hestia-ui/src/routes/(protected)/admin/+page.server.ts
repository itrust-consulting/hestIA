import type { PageServerLoad } from './$types';

export const load: PageServerLoad = async ({ locals, fetch }) => {
  const perms = locals.user?.permissions;
  const isAdmin = perms?.is_admin ?? false;
  const moderated: number[] = perms?.moderated_tenants ?? [];

  if (isAdmin) {
    const [usersRes, tenantsRes, collectionsRes] = await Promise.all([
      fetch('/api/admin/users'),
      fetch('/api/admin/tenants'),
      fetch('/api/admin/collections'),
    ]);
    return {
      isAdmin: true as const,
      userCount:       usersRes.ok       ? ((await usersRes.json()).users          ?? []).length : null,
      tenantCount:     tenantsRes.ok     ? ((await tenantsRes.json()).organizations ?? []).length : null,
      collectionCount: collectionsRes.ok ? ((await collectionsRes.json()).collections ?? []).length : null,
    };
  }

  const orgs = (locals.user?.orgs ?? []) as { id: number; name: string; abbr: string }[];
  const myOrgs = orgs.filter(o => moderated.includes(o.id));

  const orgStats = await Promise.all(
    myOrgs.map(async o => {
      const [membersRes, colRes] = await Promise.all([
        fetch(`/api/admin/tenants/${o.id}/members`),
        fetch(`/api/admin/tenants/${o.id}/collections`),
      ]);
      const memberCount = membersRes.ok ? ((await membersRes.json()).members ?? []).length : 0;
      const colData     = colRes.ok     ? await colRes.json() : {};
      return {
        id: o.id, name: o.name, abbr: o.abbr,
        memberCount,
        ownedCount:  (colData.owned      ?? []).length,
        accessCount: (colData.accessible ?? []).length,
      };
    })
  );

  return {
    isAdmin: false as const,
    myOrgs: orgStats,
    totalMembers: orgStats.reduce((s, o) => s + o.memberCount,  0),
    totalOwned:   orgStats.reduce((s, o) => s + o.ownedCount,   0),
    totalAccess:  orgStats.reduce((s, o) => s + o.accessCount,  0),
  };
};
