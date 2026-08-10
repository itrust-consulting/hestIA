import { json } from '@sveltejs/kit';

export class HelpError extends Error {
  status: number;

  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
  }
}

export function helpErrorResponse(e: unknown): Response {
  if (e instanceof HelpError) {
    return json({ detail: e.message }, { status: e.status });
  }
  console.error('Help route error:', e);
  return json({ detail: 'An internal error occurred.' }, { status: 500 });
}
