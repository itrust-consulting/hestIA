import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/public';

const API_URL = env.PUBLIC_MICROSERVICE_URL || 'http://localhost:5555'
const GET_COLLECTION_API = API_URL + '/collections'

export const GET: RequestHandler = async ( ) => {
  try {
    const res = await fetch(GET_COLLECTION_API);

    if (!res.ok) {
      return new Response(JSON.stringify({ error: 'Upstream error' }), {
        status: res.status
      });
    }

    const data = await res.json();

    // Expected format: { collections: [...] }
    return Response.json(data);
  } catch (err) {
    return Response.json({ error: 'Failed to fetch collections' }, { status: 500 });
  }
};
