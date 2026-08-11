import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const POST: RequestHandler = async ({ params, request, cookies }) => {
  const token = cookies.get('token');
  const body = await request.text();
  const res = await backendFetch(`/api/collections/${encodeURIComponent(params.name)}/sync/complete`, token, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body,
  });
  return proxyResponse(res);
};
