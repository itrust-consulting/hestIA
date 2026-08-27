import type { RequestHandler } from './$types';
import { backendFetch, proxyBinaryResponse } from '$lib/server/backend';

export const GET: RequestHandler = async ({ url, cookies }) => {
  const res = await backendFetch(`/admin/logs/export?${url.searchParams.toString()}`, cookies.get('token'));
  return proxyBinaryResponse(res);
};
