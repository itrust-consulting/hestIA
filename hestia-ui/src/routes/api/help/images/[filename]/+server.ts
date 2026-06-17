import type { RequestHandler } from './$types';
import { backendFetch, proxyBinaryResponse, proxyResponse } from '$lib/server/backend';

export const GET: RequestHandler = async ({ params, cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch(`/help/images/${params.filename}`, token);
  return proxyBinaryResponse(res);
};

export const DELETE: RequestHandler = async ({ params, cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch(`/help/images/${params.filename}`, token, { method: 'DELETE' });
  return proxyResponse(res);
};

export const PATCH: RequestHandler = async ({ params, request, cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch(`/help/images/${params.filename}`, token, {
    method: 'PATCH',
    headers: { 'content-type': 'application/json' },
    body: await request.text(),
  });
  return proxyResponse(res);
};
