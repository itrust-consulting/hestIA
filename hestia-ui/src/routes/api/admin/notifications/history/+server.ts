import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const GET: RequestHandler = async ({ url, cookies }) => {
  const res = await backendFetch(`/admin/notifications/history${url.search}`, cookies.get('token'));
  return proxyResponse(res);
};
