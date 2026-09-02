import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const POST: RequestHandler = async ({ cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch('/notifications/read-all', token, { method: 'POST' });
  return proxyResponse(res);
};
