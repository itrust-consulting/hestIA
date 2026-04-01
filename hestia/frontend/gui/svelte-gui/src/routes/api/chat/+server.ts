// src/routes/api/chat/+server.ts
import type { RequestHandler } from './$types';
import { env } from '$env/dynamic/public';

const API_URL  = env.PUBLIC_MICROSERVICE_URL || 'http://localhost:5555';
const CHAT_API_URL = API_URL + '/api/chat';

export const POST: RequestHandler = async ({ request, cookies }) => {
  try {
    // Parse incoming body
    const body = await request.json();
    const token = cookies.get('token')

    const {
      messages,
      model,
      model_kwargs,
      collection,
      query_kwargs,
      stream,
      save_chat,
      conversation_id,
      conversation_title
    } = body;

    const upstream = await fetch(CHAT_API_URL, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {})
      },
      body: JSON.stringify({
        messages, 
        model, 
        model_kwargs, 
        collection, 
        query_kwargs, 
        stream,
        save_chat,
        conversation_id,
        conversation_title
 })
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