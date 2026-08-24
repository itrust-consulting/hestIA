import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const GET: RequestHandler = async ({ params, cookies }) => {
  const res = await backendFetch(`/admin/llm/connections/${params.id}/models`, cookies.get('token'));
  return proxyResponse(res);
};
