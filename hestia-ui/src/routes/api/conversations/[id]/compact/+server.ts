import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const POST: RequestHandler = async ({ params, cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch(`/conversations/${params.id}/compact`, token, { method: 'POST' });
  return proxyResponse(res);
};
