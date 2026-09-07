import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

// Defense-in-depth only -- the real enforcement lives in the backend. The
// browser's <input accept> attribute is advisory and trivially bypassed
// (drag-and-drop, a direct request to this route), and until now this BFF
// layer added no check of its own, so a backend gap had nothing backing it
// up on this side.
const ALLOWED_EXTENSIONS = ['.docx', '.pdf', '.xlsx', '.xlsm', '.json', '.csv', '.txt', '.md', '.markdown', '.pptx'];
const MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024; // 50 MB

export const POST: RequestHandler = async ({ request, cookies }) => {
  const token = cookies.get('token');
  // Pass FormData directly — fetch sets multipart Content-Type + boundary automatically
  const formData = await request.formData();

  for (const value of formData.values()) {
    if (!(value instanceof File)) continue;
    const name = value.name.toLowerCase();
    if (!ALLOWED_EXTENSIONS.some((ext) => name.endsWith(ext))) {
      return Response.json({ detail: `Unsupported file type: ${value.name}` }, { status: 400 });
    }
    if (value.size > MAX_FILE_SIZE_BYTES) {
      return Response.json({ detail: `File too large: ${value.name}` }, { status: 400 });
    }
  }

  const res = await backendFetch('/api/upload', token, {
    method: 'POST',
    body: formData,
  });
  return proxyResponse(res);
};
