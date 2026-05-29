import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const GET: RequestHandler = async ({ cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch('/admin/users', token);
  return proxyResponse(res);
};

export const POST: RequestHandler = async ({ request, cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch('/admin/users/create', token, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: await request.text()
  });
  return proxyResponse(res);
};
