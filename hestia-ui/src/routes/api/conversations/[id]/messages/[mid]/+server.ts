import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const DELETE: RequestHandler = async ({ params, cookies }) => {
  const token = cookies.get('token');
  const res = await backendFetch(`/conversations/${params.id}/messages/${params.mid}`, token, {
    method: 'DELETE'
  });
  return proxyResponse(res);
};
