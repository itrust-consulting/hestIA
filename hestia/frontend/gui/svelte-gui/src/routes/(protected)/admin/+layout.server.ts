// src/routes/(protected)/admin/+layout.server.ts
import { error } from '@sveltejs/kit';

export function load({ locals }) {

    if (!locals.user.permissions?.system_management) {
        error(403, 'Forbidden');
    }

    return {};
}