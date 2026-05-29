import { writable } from 'svelte/store';

export type ToastStatus = 'queued' | 'uploading' | 'done' | 'error';

export type UploadToast = {
  id: string;
  filename: string;
  collection: string;
  status: ToastStatus;
  n_chunks?: number;
  error?: string;
};

export type UploadJob = {
  id: string;
  file: File;
  collection: string;
  tenants: string[];
  itrTemplate: boolean;
  metadata: Record<string, string>;
  language: string;
  selectedSheets?: string[];
  onDone?: (n_chunks: number) => void;
  onError?: (error: string) => void;
};

export const uploadToasts = writable<UploadToast[]>([]);

const _queue: UploadJob[] = [];
let _processing = false;

function _patch(id: string, patch: Partial<UploadToast>) {
  uploadToasts.update(ts => ts.map(t => (t.id === id ? { ...t, ...patch } : t)));
}

function _dismiss(id: string, delay: number) {
  setTimeout(() => uploadToasts.update(ts => ts.filter(t => t.id !== id)), delay);
}

async function _processNext() {
  if (_processing || _queue.length === 0) return;
  _processing = true;

  const job = _queue.shift()!;
  _patch(job.id, { status: 'uploading' });

  try {
    const form = new FormData();
    form.append('file', job.file);
    form.append('collection', job.collection);
    form.append('tenants', JSON.stringify(job.tenants));
    form.append('itrust_template', String(job.itrTemplate));
    form.append('metadata_overrides', JSON.stringify(job.metadata));
    form.append('language', job.language);
    if (job.selectedSheets && job.selectedSheets.length > 0) {
      form.append('selected_sheets', JSON.stringify(job.selectedSheets));
    }

    const res  = await fetch('/api/admin/collections/upload', { method: 'POST', body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail ?? String(res.status));

    _patch(job.id, { status: 'done', n_chunks: data.n_chunks });
    job.onDone?.(data.n_chunks);
    _dismiss(job.id, 4000);
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Upload failed';
    _patch(job.id, { status: 'error', error: msg });
    job.onError?.(msg);
    _dismiss(job.id, 6000);
  } finally {
    _processing = false;
    _processNext();
  }
}

export function enqueueUpload(job: UploadJob): void {
  uploadToasts.update(ts => [
    ...ts,
    { id: job.id, filename: job.file.name, collection: job.collection, status: 'queued' },
  ]);
  _queue.push(job);
  _processNext();
}
