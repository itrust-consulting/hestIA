import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const GET: RequestHandler = async ({ cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch('/help', token);
  return proxyResponse(res);
};
