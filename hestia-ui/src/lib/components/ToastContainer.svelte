<script lang="ts">
  import { uploadToasts } from '$lib/stores/uploadQueue';
  import { actionToasts } from '$lib/stores/toast';
</script>

{#if $uploadToasts.length || $actionToasts.length}
  <div class="toast-stack">
    {#each $actionToasts as t (t.id)}
      <div class="toast"
        class:toast-done={t.type === 'success'}
        class:toast-error={t.type === 'error'}
        class:toast-uploading={t.type === 'info'}
      >
        <span class="toast-icon">
          {#if t.type === 'success'}✓
          {:else if t.type === 'error'}✗
          {:else}i{/if}
        </span>
        <div class="toast-body">
          <div class="toast-message">{t.message}</div>
        </div>
      </div>
    {/each}

    {#each $uploadToasts as t (t.id)}
      <div class="toast"
        class:toast-uploading={t.status === 'uploading'}
        class:toast-done={t.status === 'done'}
        class:toast-error={t.status === 'error'}
      >
        <span class="toast-icon" class:spin={t.status === 'uploading' || t.status === 'queued'}>
          {#if t.status === 'done'}✓
          {:else if t.status === 'error'}✗
          {:else}⟳{/if}
        </span>
        <div class="toast-body">
          <div class="toast-filename">{t.filename}</div>
          <div class="toast-detail">
            {#if t.isBatch}
              {t.completed} / {t.total} documents uploaded to <strong>{t.collection}</strong>
              {#if t.failedCount}({t.failedCount} failed){/if}
            {:else if t.status === 'queued'}Queued — {t.collection}
            {:else if t.status === 'uploading'}Uploading to <strong>{t.collection}</strong>…
            {:else if t.status === 'done' && t.deduped}Duplicate of <strong>{t.duplicateOf}</strong>
            {:else if t.status === 'done'}{t.n_chunks} chunks indexed in <strong>{t.collection}</strong>
            {:else if t.status === 'error'}{t.error}
            {/if}
          </div>
        </div>
      </div>
    {/each}
  </div>
{/if}

<style>
.toast-stack {
  position: fixed;
  top: 4.5rem;
  right: 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  z-index: 2000;
  width: 320px;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 0.7rem 1rem;
  border-radius: var(--radius-lg);
  background: var(--color-white);
  border: 1px solid var(--color-neutral-200);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
  animation: toast-in 200ms ease-out;
}

.toast-uploading { border-color: var(--color-blue-300); }
.toast-done      { border-color: var(--color-green-300); background: var(--color-green-50); }
.toast-error     { border-color: var(--color-red-300);   background: var(--color-red-50); }

@keyframes toast-in {
  from { opacity: 0; transform: translateX(12px); }
  to   { opacity: 1; transform: translateX(0); }
}

.toast-icon {
  font-size: 1rem;
  width: 1.1rem;
  text-align: center;
  flex-shrink: 0;
  margin-top: 1px;
  color: var(--color-neutral-400);
}
.toast-uploading .toast-icon { color: var(--color-blue-600); }
.toast-done      .toast-icon { color: var(--color-green-600); }
.toast-error     .toast-icon { color: var(--color-red-600); }

.spin {
  display: inline-block;
  animation: spin 1s linear infinite;
}
@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

.toast-body   { flex: 1; min-width: 0; }

.toast-message {
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-neutral-900);
}

.toast-filename {
  font-size: var(--text-sm);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--color-neutral-900);
}

.toast-detail {
  font-size: var(--text-xs);
  color: var(--color-neutral-500);
  margin-top: 0.1rem;
}
.toast-done  .toast-detail { color: var(--color-green-700); }
.toast-error .toast-detail { color: var(--color-red-700); }
</style>
