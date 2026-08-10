import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { requireAdmin } from '$lib/server/help/auth';
import { putSection, deleteSection } from '$lib/server/help/sections';
import { HelpError, helpErrorResponse } from '$lib/server/help/errors';

export const PUT: RequestHandler = async ({ params, request, locals }) => {
  try {
    requireAdmin(locals);
    const { content } = await request.json();
    await putSection(params.section, content);
    return json({ ok: true });
  } catch (e) {
    return helpErrorResponse(e);
  }
};

export const DELETE: RequestHandler = async ({ params, locals }) => {
  try {
    requireAdmin(locals);
    const deleted = await deleteSection(params.section);
    if (!deleted) throw new HelpError(404, 'Section not found');
    return json({ ok: true });
  } catch (e) {
    return helpErrorResponse(e);
  }
};
