import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/public';

const API_URL = env.PUBLIC_MICROSERVICE_URL || 'http://localhost:5555'
const CONVO_API = API_URL + '/conversations';

export const GET: RequestHandler = async ( {cookies} ) => {
    const token = cookies.get('token');
    try {
        const res = await fetch(CONVO_API, {
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

        // Expected format: { collections: [...] }
        return Response.json(data);
    } catch (err) {
        return Response.json({ error: 'Failed to fetch collections' }, { status: 500 });
    }
};