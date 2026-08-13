import type { PageServerLoad } from './$types';
import type { DocumentDetail } from '$lib/types';
import { error } from '@sveltejs/kit';

export const load: PageServerLoad = async ({ fetch, params, locals }) => {
  const perms = locals.user?.permissions;
  const isAdmin = perms?.is_admin ?? false;
  const moderated: number[] = perms?.moderated_tenants ?? [];

  const colRes = await fetch(`/api/admin/collections/${encodeURIComponent(params.name)}`);
  if (!colRes.ok) error(colRes.status as any, `Collection '${params.name}' not found`);
  const col = await colRes.json();

  const ownerId: number | undefined = col.owner_tenant?.id;
  if (!isAdmin && (ownerId === undefined || !moderated.includes(ownerId))) {
    error(403, 'Forbidden');
  }

  const sourceUri = params.uri;
  const docRes = await fetch(
    `/api/admin/collections/${encodeURIComponent(params.name)}/documents?source_uri=${encodeURIComponent(sourceUri)}`,
  );
  if (!docRes.ok) error(docRes.status as any, `Document '${sourceUri}' not found`);
  const doc: DocumentDetail = await docRes.json();

  return { collectionName: col.name as string, sourceUri, doc };
};
