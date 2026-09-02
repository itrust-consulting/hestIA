import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const POST: RequestHandler = async ({ params, cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch(`/account/invitations/${params.id}/accept`, token, { method: 'POST' });
  return proxyResponse(res);
};
