<script lang="ts">
  import { invalidateAll } from '$app/navigation';
  import DocumentMetadataPanel from '$lib/components/DocumentMetadataPanel.svelte';

  const { data } = $props();
  const doc = $derived(data.doc);
</script>

<div class="admin-content">
  <a class="back-link" href={`/admin/collections/${encodeURIComponent(data.collectionName)}`}>&larr; Back to {data.collectionName}</a>

  <!-- ── Header ─────────────────────────────────────────────────────────── -->
  <div class="page-header">
    <div class="page-header-left">
      <div class="avatar">📄</div>
      <div>
        <h1 class="title">{data.sourceUri}</h1>
        <span class="collection-badge">{data.collectionName}</span>
      </div>
    </div>
  </div>

  <DocumentMetadataPanel
    collectionName={data.collectionName}
    sourceUri={data.sourceUri}
    docInfo={doc.doc_info}
    onSaved={() => invalidateAll()}
  />

  <!-- ── Chunks section ─────────────────────────────────────────────────── -->
  <section class="card">
    <h2 class="section-title">Chunks ({doc.chunks.length})</h2>
    {#if doc.chunks.length === 0}
      <p class="section-note">No chunks found for this document.</p>
    {:else}
      <div class="chunk-list">
        {#each doc.chunks as chunk (chunk.id)}
          <details class="chunk-card">
            <summary class="chunk-summary">
              <span class="chunk-id">{chunk.id}</span>
              {#if chunk.token_count != null}
                <span class="chunk-tokens">{chunk.token_count} tokens</span>
              {/if}
            </summary>
            <pre class="chunk-json">{JSON.stringify(chunk, null, 2)}</pre>
          </details>
        {/each}
      </div>
    {/if}
  </section>
</div>

<style>
.admin-content {
  flex: 1;
  overflow-y: auto;
  padding: calc(var(--spacing) * 4);
  max-width: var(--container-4xl);
  margin-inline: auto;
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.back-link { font-size: var(--text-sm); color: var(--color-neutral-500); text-decoration: none; }
.back-link:hover { color: var(--color-neutral-800); text-decoration: underline; }

/* ── Header ── */
.page-header { display: flex; justify-content: space-between; align-items: center; gap: 1rem; }
.page-header-left { display: flex; align-items: center; gap: 1rem; }
.avatar {
  width: 52px; height: 52px;
  border-radius: var(--radius-lg);
  background: color-mix(in srgb, var(--color-blue-600) 80%, transparent);
  font-size: var(--text-2xl);
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.title { font-size: var(--text-2xl); font-weight: 700; margin-bottom: 0.2rem; word-break: break-all; }
.collection-badge {
  display: inline-block;
  font-size: var(--text-xs);
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0.1rem 0.5rem;
  border-radius: 999px;
  background: var(--color-neutral-100);
  color: var(--color-neutral-600);
}

/* ── Cards ── */
.card {
  background: var(--color-neutral-50);
  padding: 1.5rem 1.75rem;
  border-radius: var(--radius-2xl);
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}
.section-title {
  font-size: var(--text-base);
  font-weight: 700;
  color: var(--color-neutral-800);
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--color-neutral-200);
}
.section-note {
  font-size: var(--text-sm);
  color: var(--color-neutral-500);
}

/* ── Chunks ── */
.chunk-list { display: flex; flex-direction: column; gap: 0.6rem; }
.chunk-card {
  background: var(--color-white); border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-lg); overflow: hidden;
}
.chunk-summary {
  display: flex; align-items: center; gap: 0.75rem;
  padding: 0.65rem 1rem; cursor: pointer; list-style: none;
  font-size: var(--text-xs);
  transition: background 100ms ease;
}
.chunk-summary::-webkit-details-marker { display: none; }
.chunk-summary::before {
  content: '▸'; display: inline-block; flex-shrink: 0;
  color: var(--color-neutral-400); transition: transform 100ms ease;
}
.chunk-card[open] .chunk-summary::before { transform: rotate(90deg); }
.chunk-summary:hover { background: var(--color-neutral-50); }
.chunk-id {
  font-family: var(--font-mono, ui-monospace, monospace); font-weight: 600;
  color: var(--color-neutral-800); overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.chunk-tokens { color: var(--color-neutral-400); white-space: nowrap; margin-left: auto; }
.chunk-json {
  margin: 0; padding: 0.75rem 1rem;
  border-top: 1px solid var(--color-neutral-200);
  font-family: var(--font-mono, ui-monospace, monospace); font-size: var(--text-xs);
  color: var(--color-neutral-900); white-space: pre-wrap; word-break: break-word; line-height: 1.6;
}
</style>
