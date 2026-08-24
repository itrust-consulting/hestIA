import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const PUT: RequestHandler = async ({ params, request, cookies }) => {
  const res = await backendFetch(`/admin/llm/connections/${params.id}`, cookies.get('token'), {
    method: 'PUT',
    headers: { 'content-type': 'application/json' },
    body: await request.text()
  });
  return proxyResponse(res);
};

export const DELETE: RequestHandler = async ({ params, cookies }) => {
  const res = await backendFetch(`/admin/llm/connections/${params.id}`, cookies.get('token'), { method: 'DELETE' });
  return proxyResponse(res);
};
