import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const POST: RequestHandler = async ({ params, request, cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch(`/organizations/${params.id}/join-requests`, token, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: await request.text(),
  });
  return proxyResponse(res);
};
