import { json } from '@sveltejs/kit';
import fs from 'node:fs/promises';
import path from 'node:path';
import type { RequestHandler } from './$types';
import { requireUser, requireAdmin } from '$lib/server/help/auth';
import { imagePath, renameImage, deleteImage } from '$lib/server/help/images';
import { HelpError, helpErrorResponse } from '$lib/server/help/errors';

const MIME_TYPES: Record<string, string> = {
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.jpeg': 'image/jpeg',
  '.gif': 'image/gif',
  '.webp': 'image/webp'
};

export const GET: RequestHandler = async ({ params, locals }) => {
  try {
    requireUser(locals);
    const p = imagePath(params.filename);
    let data: Buffer;
    try {
      data = await fs.readFile(p);
    } catch {
      throw new HelpError(404, 'Image not found');
    }
    const contentType = MIME_TYPES[path.extname(p).toLowerCase()] ?? 'application/octet-stream';
    return new Response(new Uint8Array(data), { headers: { 'content-type': contentType } });
  } catch (e) {
    return helpErrorResponse(e);
  }
};

export const PATCH: RequestHandler = async ({ params, request, locals }) => {
  try {
    requireAdmin(locals);
    const { filename } = await request.json();
    const url = await renameImage(params.filename, filename);
    return json({ ok: true, url });
  } catch (e) {
    return helpErrorResponse(e);
  }
};

export const DELETE: RequestHandler = async ({ params, locals }) => {
  try {
    requireAdmin(locals);
    await deleteImage(params.filename);
    return json({ ok: true });
  } catch (e) {
    return helpErrorResponse(e);
  }
};
