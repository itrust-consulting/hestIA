import { json } from '@sveltejs/kit';
import path from 'node:path';
import type { RequestHandler } from './$types';
import { requireUser, requireAdmin } from '$lib/server/help/auth';
import { listImages, saveImage, SAFE_EXT, MAX_BYTES } from '$lib/server/help/images';
import { HelpError, helpErrorResponse } from '$lib/server/help/errors';

export const GET: RequestHandler = async ({ locals }) => {
  try {
    requireUser(locals);
    const images = await listImages();
    return json({ images });
  } catch (e) {
    return helpErrorResponse(e);
  }
};

export const POST: RequestHandler = async ({ request, locals }) => {
  try {
    requireAdmin(locals);
    const form = await request.formData();
    const file = form.get('file');
    if (!(file instanceof File)) {
      throw new HelpError(400, 'Missing file');
    }
    const ext = path.extname(file.name || '').toLowerCase() || '.png';
    if (!SAFE_EXT.has(ext)) {
      throw new HelpError(400, `Unsupported format. Allowed: ${[...SAFE_EXT].join(', ')}`);
    }
    const buffer = Buffer.from(await file.arrayBuffer());
    if (buffer.byteLength > MAX_BYTES) {
      throw new HelpError(413, 'Image too large (max 10 MB)');
    }
    const { filename, url } = await saveImage(buffer, ext);
    return json({ url, filename });
  } catch (e) {
    return helpErrorResponse(e);
  }
};
