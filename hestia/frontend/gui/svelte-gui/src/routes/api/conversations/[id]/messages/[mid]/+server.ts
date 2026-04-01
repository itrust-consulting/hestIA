import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/public';

const API_URL = env.PUBLIC_MICROSERVICE_URL || 'http://localhost:5555'
const CONVO_API = API_URL + '/conversations';

export const DELETE: RequestHandler = async ({ params, cookies }) => {
  const token = cookies.get('token');
  const { id, mid } = params;

  const upstream = await fetch(`${CONVO_API}/${id}/messages/${mid}`, {
    method: 'DELETE',
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    }
  });

  return new Response(await upstream.text(), { status: upstream.status });
};
