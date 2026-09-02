import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const GET: RequestHandler = async ({ params, url, cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch(`/admin/organizations/${params.id}/join-requests${url.search}`, token);
  return proxyResponse(res);
};
