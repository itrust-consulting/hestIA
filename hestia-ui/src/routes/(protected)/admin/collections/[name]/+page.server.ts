import type { PageServerLoad } from './$types';
import type { AccessGrant, Collection, Org } from '$lib/types';
import { error } from '@sveltejs/kit';

export const load: PageServerLoad = async ({ fetch, params, locals }) => {
  const perms = locals.user?.permissions;
  const isAdmin = perms?.is_admin ?? false;
  const moderated: number[] = perms?.moderated_tenants ?? [];

  const res = await fetch(`/api/admin/collections/${encodeURIComponent(params.name)}`);
  if (!res.ok) error(res.status as any, `Collection '${params.name}' not found`);
  const raw = await res.json();

  // Mods may only access collections owned by their moderated tenants
  const ownerId: number | undefined = raw.owner_tenant?.id;
  if (!isAdmin && (ownerId === undefined || !moderated.includes(ownerId))) {
    error(403, 'Forbidden');
  }

  const canManage = isAdmin || (ownerId !== undefined && moderated.includes(ownerId));

  // Fetch full access-tenant objects from the owner's collection grants.
  let access: AccessGrant[] = [];
  if (ownerId) {
    const grantsRes = await fetch(`/api/admin/tenants/${ownerId}/collections`);
    if (grantsRes.ok) {
      const grants = await grantsRes.json();
      const owned = (grants.owned ?? []).find((c: any) => c.id === params.name);
      access = (owned?.access ?? []).map((t: any) => ({
        id: t.id,
        name: t.name,
        abbreviation: t.abbreviation,
        max_classification: t.max_classification ?? null,
      }));
    }
  }

  // Fetch all organisations for the grant dropdown (all orgs — moderators may grant access to any tenant).
  const orgsRes = await fetch('/api/admin/tenants');
  const rawOrgs: any[] = orgsRes.ok ? ((await orgsRes.json()).organizations ?? []) : [];
  const allOrganizations: Org[] = rawOrgs.map((o: any) => ({
    id: o.id,
    name: o.name,
    abbreviation: o.abbreviation,
  }));

  const collection: Collection = {
    id: raw.name,
    points_count: raw.points_count ?? 0,
    status: raw.status ?? 'unknown',
    ownerTenant: raw.owner_tenant ?? null,
    access,
    documents: raw.documents ?? [],
  };

  return { collection, allOrganizations, isAdmin, canManage };
};
