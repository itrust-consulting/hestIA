import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const POST: RequestHandler = async ({ params, cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch(
    `/admin/organizations/${params.org_id}/members/${params.user_id}`,
    token,
    { method: 'POST' }
  );
  return proxyResponse(res);
};

export const DELETE: RequestHandler = async ({ params, cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch(
    `/admin/organizations/${params.org_id}/members/${params.user_id}`,
    token,
    { method: 'DELETE' }
  );
  return proxyResponse(res);
};
