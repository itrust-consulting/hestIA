import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const GET: RequestHandler = async ({ params, cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch(`/admin/organizations/${params.id}/members`, token);
  return proxyResponse(res);
};

export const POST: RequestHandler = async ({ params, request, cookies }) => {
  const token = cookies.get('token');
  const { user_id } = await request.json();
  const res = await backendFetch(`/admin/organizations/${params.id}/members/${user_id}`, token, {
    method: 'POST',
  });
  return proxyResponse(res);
};
