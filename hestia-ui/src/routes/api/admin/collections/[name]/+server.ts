import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const GET: RequestHandler = async ({ params, cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch(`/api/collections/${encodeURIComponent(params.name)}`, token);
  return proxyResponse(res);
};

export const DELETE: RequestHandler = async ({ params, cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch(`/api/collections/${encodeURIComponent(params.name)}`, token, {
    method: 'DELETE',
  });
  return proxyResponse(res);
};
