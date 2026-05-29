import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const PUT: RequestHandler = async ({ params, cookies, request }) => {
  const token = cookies.get('token');
  const body = await request.json().catch(() => ({}));
  const res = await backendFetch(
    `/admin/organizations/${params.id}/collections/${encodeURIComponent(params.col)}`,
    token,
    {
      method: 'PUT',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    }
  );
  return proxyResponse(res);
};

export const DELETE: RequestHandler = async ({ params, cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch(
    `/admin/organizations/${params.id}/collections/${encodeURIComponent(params.col)}`,
    token,
    { method: 'DELETE' }
  );
  return proxyResponse(res);
};
