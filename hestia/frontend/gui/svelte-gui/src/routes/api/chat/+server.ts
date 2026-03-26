// src/routes/api/chat/+server.ts
import type { RequestHandler } from './$types';
import { PUBLIC_MICROSERVICE_URL } from '$env/static/public';

const CHAT_API = PUBLIC_MICROSERVICE_URL + '/api/chat'

export const POST: RequestHandler = async ({ request }) => {
  try {
    // Parse incoming body
    const body = await request.json();
    const { messages, model, model_kwargs, collection, query_kwargs, stream } = body;

    // Forward to your microservice (which must support streaming)
    const upstream = await fetch(CHAT_API, {
      method: 'POST',
      headers: {
        'content-type': 'application/json'
      },
      body: JSON.stringify({ messages, model, model_kwargs, collection, query_kwargs, stream })
    });

    if (!upstream.ok || !upstream.body) {
      return new Response(`Upstream error: ${upstream.status}`, {
        status: upstream.status
      });
    }

    // Stream the response back to the client
    const readableStream = new ReadableStream({
      async start(controller) {
        const reader = upstream.body!.getReader();
        const decoder = new TextDecoder();

        try {
          while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            // Directly forward raw chunks
            controller.enqueue(value);
          }
        } catch (err) {
          console.error("Streaming error:", err);
        } finally {
          controller.close();
        }
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
    console.error("API error:", err);
    return new Response(`API error: ${err.message}`, { status: 500 });
  }
};
``