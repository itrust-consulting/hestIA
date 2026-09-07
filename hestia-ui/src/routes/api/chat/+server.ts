import type { RequestHandler } from './$types';
import { backendFetch, proxyResponse } from '$lib/server/backend';

export const POST: RequestHandler = async ({ request, cookies }) => {
  try {
    const body = await request.json();
    const token = cookies.get('token');

    // Tied to the browser disconnecting (Stop button) via the stream's
    // cancel() below -- lets the abort actually reach the backend/vLLM
    // instead of the request continuing in the background.
    const backendAbort = new AbortController();

    const upstream = await backendFetch('/api/chat', token, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
      signal: backendAbort.signal
    });

    if (!upstream.ok || !upstream.body) {
      // Matches every other route's { detail } JSON contract (via
      // proxyResponse) instead of this route's own raw-text shape, which a
      // caller expecting JSON would fail to parse.
      return proxyResponse(upstream);
    }

    let cancelled = false;
    const reader = upstream.body.getReader();

    const readableStream = new ReadableStream({
      async start(controller) {
        try {
          while (true) {
            const { value, done } = await reader.read();
            if (done || cancelled) break;
            controller.enqueue(value);
          }
        } catch (err) {
          if (!cancelled) console.error('Streaming error:', err);
        } finally {
          if (!cancelled) controller.close();
        }
      },
      cancel(reason) {
        // The runtime calls this once the client (browser) disconnects --
        // stop reading and abort the upstream request so the backend (and
        // vLLM) actually stop generating, instead of running to completion
        // unseen. Without this handler the controller gets torn down by
        // the runtime anyway, but start()'s loop keeps calling
        // enqueue()/close() against it, throwing ERR_INVALID_STATE.
        cancelled = true;
        console.info('Chat stream cancelled by client, aborting upstream request.', reason);
        backendAbort.abort();
        reader.cancel().catch(() => {});
      }
    });

    return new Response(readableStream, {
      headers: {
        'content-type': 'text/plain; charset=utf-8',
        'cache-control': 'no-cache',
        'transfer-encoding': 'chunked'
      }
    });
  } catch (err: any) {
    // Matches proxyResponse's convention of never putting raw error text in
    // a 500 body -- this route used to leak err.message (potentially
    // stack-adjacent internals) directly to the client here.
    console.error('API error:', err);
    return new Response(JSON.stringify({ detail: 'An internal error occurred.' }), {
      status: 500,
      headers: { 'content-type': 'application/json' }
    });
  }
};
