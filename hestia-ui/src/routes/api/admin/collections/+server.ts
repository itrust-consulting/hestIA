import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const GET: RequestHandler = async ({ cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch('/api/collections', token);
  return proxyResponse(res);
};

export const POST: RequestHandler = async ({ request, cookies }) => {
  const token = cookies.get('token');
  const body = await request.json();
  const res = await backendFetch('/admin/collections/create', token, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body),
  });
  return proxyResponse(res);
};
