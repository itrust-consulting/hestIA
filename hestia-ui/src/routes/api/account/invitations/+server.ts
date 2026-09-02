import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const GET: RequestHandler = async ({ url, cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch(`/account/invitations${url.search}`, token);
  return proxyResponse(res);
};
