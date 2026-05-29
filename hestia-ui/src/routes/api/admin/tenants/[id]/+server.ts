import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const PUT: RequestHandler = async ({ params, request, cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch(`/admin/organizations/${params.id}`, token, {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: await request.text(),
  });
  return proxyResponse(res);
};

export const DELETE: RequestHandler = async ({ params, cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch(`/admin/organizations/${params.id}`, token, { method: 'DELETE' });
  return proxyResponse(res);
};
