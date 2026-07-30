import type { PageServerLoad } from './$types';
import type { Collection, Org } from '$lib/types';
import { error } from '@sveltejs/kit';

export const load: PageServerLoad = async ({ params, fetch, url, locals }) => {
  const perms = locals.user?.permissions;
  const isAdmin = perms?.is_admin ?? false;
  const moderated: number[] = perms?.moderated_tenants ?? [];

  if (!isAdmin && !moderated.includes(Number(params.id))) {
    error(403, 'Forbidden');
  }

  const [tenantRes, membersRes, usersRes, tenantColsRes, collectionsRes, countsRes] = await Promise.all([
    fetch('/api/admin/tenants'),
    fetch(`/api/admin/tenants/${params.id}/members`),
    fetch('/api/admin/users'),
    fetch(`/api/admin/tenants/${params.id}/collections`),
    fetch('/api/collections'),
    fetch('/api/admin/collections/document-counts'),
  ]);

  if (!tenantRes.ok) error(tenantRes.status, 'Could not load tenants.');
  const allTenants = (await tenantRes.json()).organizations ?? [];
  const tenant = allTenants.find((t: any) => String(t.id) === params.id);
  if (!tenant) error(404, 'Tenant not found.');

  const members = membersRes.ok ? ((await membersRes.json()).members ?? []) : [];
  const allUsers = usersRes.ok ? ((await usersRes.json()).users ?? []) : [];
  const allCollections = collectionsRes.ok ? (await collectionsRes.json()).collections ?? [] : [];

  let ownedRaw: any[] = [];
  let accessibleRaw: any[] = [];
  if (tenantColsRes.ok) {
    const colData = await tenantColsRes.json();
    ownedRaw = colData.owned ?? [];
    accessibleRaw = colData.accessible ?? [];
  }

  const counts: Record<string, number> = countsRes.ok ? (await countsRes.json()).counts ?? {} : {};

  const ownerTenant: Org = { id: tenant.id, name: tenant.name, abbreviation: tenant.abbreviation };

  const ownedCollections: Collection[] = ownedRaw.map((col: any) => ({
    id: col.id,
    points_count: col.points_count ?? 0,
    status: col.status ?? 'unknown',
    ownerTenant,
    access: col.access ?? [],
    documents: [],
    documentCount: counts[col.id] ?? 0,
  }));

  const accessibleCollections: Collection[] = accessibleRaw.map((col: any) => ({
    id: col.id,
    points_count: col.points_count ?? 0,
    status: col.status ?? 'unknown',
    ownerTenant: col.owner ?? null,
    access: [],
    documents: [],
    documentCount: counts[col.id] ?? 0,
  }));

  const uploadOrganizations = isAdmin
    ? allTenants.map((t: any) => ({ id: t.id, name: t.name, abbreviation: t.abbreviation }))
    : (locals.user?.orgs ?? [] as any[])
        .filter((o: any) => moderated.includes(o.id))
        .map((o: any) => ({ id: o.id, name: o.name, abbreviation: o.abbr }));

  return {
    tenant,
    members,
    allUsers,
    allCollections,
    ownedCollections,
    accessibleCollections,
    uploadOrganizations,
    editMode: url.searchParams.has('edit'),
  };
};
