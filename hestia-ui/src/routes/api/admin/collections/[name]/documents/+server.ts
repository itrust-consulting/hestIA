import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const GET: RequestHandler = async ({ params, url, cookies }) => {
  const token = cookies.get('token');
  const sourceUri = url.searchParams.get('source_uri') ?? '';
  const backendUrl = `/api/collections/${encodeURIComponent(params.name)}/documents?source_uri=${encodeURIComponent(sourceUri)}`;
  const res = await backendFetch(backendUrl, token, { method: 'GET' });
  return proxyResponse(res);
};

export const DELETE: RequestHandler = async ({ params, url, cookies }) => {
  const token = cookies.get('token');
  const sourceUri = url.searchParams.get('source_uri') ?? '';
  const backendUrl = `/api/collections/${encodeURIComponent(params.name)}/documents?source_uri=${encodeURIComponent(sourceUri)}`;
  const res = await backendFetch(backendUrl, token, { method: 'DELETE' });
  return proxyResponse(res);
};

export const PATCH: RequestHandler = async ({ params, request, cookies }) => {
  const token = cookies.get('token');
  const body = await request.text();
  const backendUrl = `/api/collections/${encodeURIComponent(params.name)}/documents`;
  const res = await backendFetch(backendUrl, token, {
    method: 'PATCH',
    headers: { 'content-type': 'application/json' },
    body,
  });
  return proxyResponse(res);
};
