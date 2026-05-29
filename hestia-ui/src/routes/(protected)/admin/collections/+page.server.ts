import type { PageServerLoad } from './$types';
import type { Collection } from '$lib/types';

export const load: PageServerLoad = async ({ locals, fetch }) => {
  const perms = locals.user?.permissions;
  const isAdmin = perms?.is_admin ?? false;
  const moderated: number[] = perms?.moderated_tenants ?? [];

  const [collectionsRes, orgsRes] = await Promise.all([
    fetch('/api/admin/collections'),
    fetch('/api/admin/tenants'),
  ]);

  const allQdrant: any[] = collectionsRes.ok
    ? ((await collectionsRes.json()).collections ?? [])
    : [];

  const allOrgs: any[] = orgsRes.ok
    ? ((await orgsRes.json()).organizations ?? [])
    : [];

  // Mods only see collections owned by their moderated tenants
  const visibleOrgs = isAdmin ? allOrgs : allOrgs.filter((o: any) => moderated.includes(o.id));

  // Fetch SQL grants (owner + access) and individual collection details (documents) in parallel
  const [orgCollections, collectionDetails] = await Promise.all([
    Promise.all(
      visibleOrgs.map(async (org: any) => {
        const res = await fetch(`/api/admin/tenants/${org.id}/collections`);
        if (!res.ok) return { org, owned: [] };
        const data = await res.json();
        return { org, owned: data.owned ?? [] };
      })
    ),
    Promise.all(
      allQdrant.map(async (qc: any) => {
        const res = await fetch(`/api/admin/collections/${encodeURIComponent(qc.name)}`);
        if (!res.ok) return { name: qc.name, documents: [] };
        const data = await res.json();
        return { name: qc.name, documents: data.documents ?? [] };
      })
    ),
  ]);

  // Build collection → {ownerTenant, access} map from SQL grants
  const grantMap = new Map<string, { ownerTenant: any; access: any[] }>();
  for (const { org, owned } of orgCollections) {
    for (const col of owned) {
      grantMap.set(col.id, {
        ownerTenant: { id: org.id, name: org.name, abbreviation: org.abbreviation },
        access: col.access ?? [],
      });
    }
  }

  const documentsMap = new Map(collectionDetails.map(d => [d.name, d.documents]));

  // ownerOrgs: scoped to moderated tenants for moderators (can only own on behalf of their org)
  const ownerOrgs = (isAdmin ? allOrgs : visibleOrgs).map((o: any) => ({
    id: o.id,
    name: o.name,
    abbreviation: o.abbreviation,
  }));
  // allOrganizations: all orgs for access grants (moderators may grant access to any tenant)
  const allOrganizations = allOrgs.map((o: any) => ({
    id: o.id,
    name: o.name,
    abbreviation: o.abbreviation,
  }));

  // Mods only see collections that have an owner in their moderated tenants
  const visibleQdrant = isAdmin ? allQdrant : allQdrant.filter(qc => grantMap.has(qc.name));

  const collections: Collection[] = visibleQdrant.map((qc: any) => {
    const grants = grantMap.get(qc.name) ?? { ownerTenant: null, access: [] };
    return {
      id: qc.name,
      points_count: qc.points_count ?? 0,
      status: qc.status ?? 'unknown',
      ownerTenant: grants.ownerTenant,
      access: grants.access,
      documents: documentsMap.get(qc.name) ?? [],
    };
  });

  return { collections, ownerOrgs, allOrganizations };
};
