import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const PATCH: RequestHandler = async ({ params, request, cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch(
    `/admin/organizations/${params.id}/members/${params.uid}/classification`,
    token,
    { method: 'PATCH', headers: { 'content-type': 'application/json' }, body: await request.text() }
  );
  return proxyResponse(res);
};
