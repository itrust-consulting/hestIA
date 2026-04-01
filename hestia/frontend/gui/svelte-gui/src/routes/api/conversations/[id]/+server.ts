import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/public';

const API_URL = env.PUBLIC_MICROSERVICE_URL || 'http://localhost:5555'
const CONVO_API = API_URL + '/conversations/';

export const GET: RequestHandler = async ( {params, cookies} ) => {
    const token = cookies.get('token');
    const { id } = params;

    if (!id) {
        return new Response("Conversation ID required", { status: 400 });
    }

    try {
        const res = await fetch(CONVO_API + id, {
            method: 'GET',
            headers: {
            'content-type': 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        }
        );
        if (!res.ok) {
        return new Response(JSON.stringify({ error: 'Upstream error' }), {
            status: res.status
        });
        }

        const data = await res.json();

        return Response.json(data);
    } catch (err) {
        return Response.json({ error: 'Failed to fetch collections' }, { status: 500 });
    }
};

export const PATCH: RequestHandler = async ({ params, cookies, request }) => {
  const token = cookies.get('token');
  const { id } = params;

  const upstream = await fetch(CONVO_API + id, {
    method: 'PATCH',
    headers: {
      'content-type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {})
    },
    body: await request.text()
  });

  return new Response(await upstream.text(), { status: upstream.status });
};

export const DELETE: RequestHandler = async ({ params, cookies }) => {
  const token = cookies.get('token');
  const { id } = params;

  const upstream = await fetch(CONVO_API + id, {
    method: 'DELETE',
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) }
  });

  return new Response(await upstream.text(), { status: upstream.status });
};
