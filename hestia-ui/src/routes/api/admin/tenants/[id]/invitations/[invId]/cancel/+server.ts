import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const POST: RequestHandler = async ({ params, cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch(
    `/admin/organizations/${params.id}/invitations/${params.invId}/cancel`,
    token,
    { method: 'POST' }
  );
  return proxyResponse(res);
};
