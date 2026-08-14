import { writable } from 'svelte/store';

export type ToastStatus = 'queued' | 'uploading' | 'done' | 'error';

export type UploadToast = {
  id: string;
  filename: string;
  collection: string;
  status: ToastStatus;
  n_chunks?: number;
  error?: string;
  /** Set when this upload's content already existed elsewhere in the collection. */
  deduped?: boolean;
  duplicateOf?: string;
  /** Set for a single toast tracking many jobs at once (see createBatchToast). */
  isBatch?: boolean;
  total?: number;
  completed?: number;
  failedCount?: number;
};

export type UploadDoneInfo = { deduped: boolean; duplicateOf?: string };

export type UploadJob = {
  id: string;
  file: File;
  /** Relative path (e.g. "docs/guide.md") when the file came from a folder pick/drop. */
  relPath?: string;
  collection: string;
  tenants: string[];
  itrTemplate: boolean;
  metadata: Record<string, string>;
  language: string;
  chunkingStrategy?: string;
  selectedSheets?: string[];
  /** Content-hash tracking — sent for every upload (Sync Folder uses a
   *  per-folder id; the plain upload modal uses a fixed 'manual' id) so
   *  identical content is only ever embedded/stored once per collection. */
  syncId?: string;
  contentHash?: string;
  onDone?: (n_chunks: number, info?: UploadDoneInfo) => void;
  onError?: (error: string) => void;
};

export const uploadToasts = writable<UploadToast[]>([]);

const _queue: (UploadJob & { batchId?: string })[] = [];
let _processing = false;

function _patch(id: string, patch: Partial<UploadToast>) {
  uploadToasts.update(ts => ts.map(t => (t.id === id ? { ...t, ...patch } : t)));
}

function _dismiss(id: string, delay: number) {
  setTimeout(() => uploadToasts.update(ts => ts.filter(t => t.id !== id)), delay);
}

/** One shared toast for a bulk upload (auto-upload, Sync Folder) that reports
 * "x / y documents uploaded" instead of a separate toast per file. Pass the
 * returned id as the second argument to enqueueUpload for every job in the batch. */
export function createBatchToast(collection: string, total: number): string {
  const batchId = crypto.randomUUID();
  uploadToasts.update(ts => [
    ...ts,
    {
      id: batchId, filename: `${total} document${total === 1 ? '' : 's'}`, collection,
      status: 'uploading', isBatch: true, total, completed: 0, failedCount: 0,
    },
  ]);
  return batchId;
}

function _bumpBatch(batchId: string, ok: boolean) {
  let updated: UploadToast | undefined;
  uploadToasts.update(ts => ts.map(t => {
    if (t.id !== batchId) return t;
    const completed = (t.completed ?? 0) + 1;
    const failedCount = (t.failedCount ?? 0) + (ok ? 0 : 1);
    const finished = completed >= (t.total ?? completed);
    updated = { ...t, completed, failedCount, status: finished ? (failedCount > 0 ? 'error' : 'done') : 'uploading' };
    return updated;
  }));
  if (updated && (updated.completed ?? 0) >= (updated.total ?? 0)) {
    _dismiss(batchId, (updated.failedCount ?? 0) > 0 ? 8000 : 4000);
  }
}

async function _processNext() {
  if (_processing || _queue.length === 0) return;
  _processing = true;

  const job = _queue.shift()!;
  if (!job.batchId) _patch(job.id, { status: 'uploading' });

  try {
    const form = new FormData();
    form.append('file', job.file, job.relPath || job.file.name);
    form.append('collection', job.collection);
    form.append('tenants', JSON.stringify(job.tenants));
    form.append('itrust_template', String(job.itrTemplate));
    form.append('metadata_overrides', JSON.stringify(job.metadata));
    form.append('language', job.language);
    if (job.chunkingStrategy) {
      form.append('chunking_strategy', job.chunkingStrategy);
    }
    if (job.selectedSheets && job.selectedSheets.length > 0) {
      form.append('selected_sheets', JSON.stringify(job.selectedSheets));
    }
    if (job.syncId && job.contentHash) {
      form.append('sync_id', job.syncId);
      form.append('content_hash', job.contentHash);
    }

    const res  = await fetch('/api/admin/collections/upload', { method: 'POST', body: form });
    if (!res.ok) {
      let detail = String(res.status);
      try { detail = (await res.json()).detail ?? detail; } catch { /* non-JSON error body */ }
      throw new Error(detail);
    }
    const data = await res.json();

    if (job.batchId) {
      _bumpBatch(job.batchId, true);
    } else {
      _patch(job.id, { status: 'done', n_chunks: data.n_chunks, deduped: data.deduped, duplicateOf: data.duplicate_of });
      _dismiss(job.id, 4000);
    }
    job.onDone?.(data.n_chunks, { deduped: !!data.deduped, duplicateOf: data.duplicate_of });
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : 'Upload failed';
    if (job.batchId) {
      _bumpBatch(job.batchId, false);
    } else {
      _patch(job.id, { status: 'error', error: msg });
      _dismiss(job.id, 6000);
    }
    job.onError?.(msg);
  } finally {
    _processing = false;
    _processNext();
  }
}

/** Queue a single upload. Pass a batchId (from createBatchToast) to fold this
 * job into a shared batch toast instead of creating its own toast. */
export function enqueueUpload(job: UploadJob, batchId?: string): void {
  if (batchId) {
    _queue.push({ ...job, batchId });
  } else {
    uploadToasts.update(ts => [
      ...ts,
      { id: job.id, filename: job.relPath || job.file.name, collection: job.collection, status: 'queued' },
    ]);
    _queue.push(job);
  }
  _processNext();
}
