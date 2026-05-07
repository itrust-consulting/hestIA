import type { Handle } from '@sveltejs/kit';
import { env } from '$env/dynamic/public';

const API_URL = env.PUBLIC_MICROSERVICE_URL || 'http://localhost:5555';
const ACCOUNT_API = `${API_URL}/account`;

export const handle: Handle = async ({ event, resolve }) => {
    const token = event.cookies.get('token');

    event.locals.user = null;

    if (token) {
        try {
            const upstream = await fetch(ACCOUNT_API, {
                headers: {
                    Authorization: `Bearer ${token}`
                }
            });

            if (upstream.ok) {
                event.locals.user = await upstream.json();
            } else {
                // Token invalid / expired → clear cookie defensively
                event.cookies.delete('token', { path: '/' });
            }
        } catch (err) {
            console.error('Failed to fetch user profile', err);
        }
    }

    return resolve(event);
};