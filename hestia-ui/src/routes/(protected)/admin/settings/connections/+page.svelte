<script lang="ts">
  import { invalidateAll } from '$app/navigation';
  import Modal from '$lib/components/Modal.svelte';
  import ConfirmDeleteModal from '$lib/components/modals/ConfirmDeleteModal.svelte';
  import { addToast } from '$lib/stores/toast';
  import PlusLgIcon from '$lib/components/icons/plusLgIcon.svelte';
  import SettingsIcon from '$lib/components/icons/settingsIcon.svelte';
  import ShowIcon from '$lib/components/icons/showIcon.svelte';
  import { getParamSpecs, paramValueToString, parseParamValue, buildObjectParam, parseJsonParam } from '$lib/llmParamSchemas';

  const { data } = $props();

  type Purpose = 'generation' | 'embedding' | 'reranking' | 'vector_db';
  type BackendType = 'ollama' | 'openai' | 'qdrant';

  type Connection = {
    id: number;
    purpose: Purpose;
    label: string;
    backend_type: BackendType;
    base_url: string;
    has_api_key: boolean;
    model: string;
    params: Record<string, unknown>;
    is_active: boolean;
    compaction_enabled: boolean;
    compaction_model: string | null;
    compaction_context_window: number | null;
    compaction_summary_length: number | null;
  };

  const PURPOSES: { key: Purpose; label: string }[] = [
    { key: 'generation', label: 'Generation' },
    { key: 'embedding', label: 'Embedding' },
    { key: 'reranking', label: 'Reranking' },
    { key: 'vector_db', label: 'Vector Database' },
  ];
  // Which purposes are valid for connections of a given backend type --
  // e.g. 'vector_db' only makes sense for a Qdrant connection.
  const PURPOSES_BY_BACKEND: Record<BackendType, Purpose[]> = {
    ollama: ['generation', 'embedding', 'reranking'],
    openai: ['generation', 'embedding', 'reranking'],
    qdrant: ['vector_db'],
  };
  const connections: Connection[] = $derived(data.connections ?? []);
  const ollamaConnections = $derived(connections.filter((c) => c.backend_type === 'ollama'));
  const openaiConnections = $derived(connections.filter((c) => c.backend_type === 'openai'));
  const qdrantConnections = $derived(connections.filter((c) => c.backend_type === 'qdrant'));
  // A purpose may have several connections (at most one active) -- the Add
  // flow always offers every purpose valid for the chosen backend type,
  // regardless of whether it's already configured.
  function purposesFor(backendType: BackendType) {
    return PURPOSES.filter((p) => PURPOSES_BY_BACKEND[backendType].includes(p.key));
  }

  // ── Add connection ──────────────────────────────────────────────────────
  let addModalOpen = $state(false);
  let addBackendType = $state<BackendType>('ollama');
  let addPurpose = $state<Purpose | ''>('');
  let addBaseUrl = $state('');
  let addApiKey = $state('');
  let addApiKeyVisible = $state(false);
  let addPhase = $state<'testing' | 'creating' | null>(null);
  let addError = $state<string | null>(null);

  function openAddConnection(backendType: BackendType) {
    addBackendType = backendType;
    addPurpose = purposesFor(backendType)[0]?.key ?? '';
    addBaseUrl = '';
    addApiKey = '';
    addApiKeyVisible = false;
    addError = null;
    addModalOpen = true;
  }

  async function handleAddConnection() {
    if (!addPurpose || !addBaseUrl.trim()) return;
    addError = null;
    addPhase = 'testing';
    try {
      const testRes = await fetch('/api/admin/llm-connections/test', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          backend_type: addBackendType,
          base_url: addBaseUrl.trim(),
          api_key: addApiKey.trim() || null,
        }),
      });
      const testData = await testRes.json().catch(() => ({}));
      if (!testRes.ok || testData.ok === false) {
        throw new Error(testData.error ?? testData.detail ?? 'Could not connect to this backend.');
      }

      addPhase = 'creating';
      const res = await fetch('/api/admin/llm-connections', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          purpose: addPurpose,
          backend_type: addBackendType,
          base_url: addBaseUrl.trim(),
          api_key: addApiKey.trim() || null,
        }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      addToast('Connection created.', 'success');
      addModalOpen = false;
      await invalidateAll();
    } catch (e: any) {
      addError = e.message ?? 'Failed to create connection.';
    } finally {
      addPhase = null;
    }
  }

  // ── Settings modal (edit URL/API key/model/params, or delete) ───────────
  let settingsOpen = $state(false);
  let settingsConn = $state<Connection | null>(null);
  let settingsBaseUrl = $state('');
  let settingsApiKey = $state('');
  let settingsApiKeyVisible = $state(false);
  let settingsModel = $state('');
  let settingsModels = $state<string[]>([]);
  let settingsModelsLoading = $state(false);
  let settingsModelsError = $state<string | null>(null);
  let settingsPhase = $state<'testing' | 'saving' | null>(null);
  let settingsError = $state<string | null>(null);
  let confirmDeleteOpen = $state(false);

  // Compaction (purpose === 'generation' only) -- bespoke fields, not routed
  // through the generic ParamSpec param list, since compaction_model needs a
  // dropdown fed by settingsModels and the rest is conditionally shown.
  let settingsCompactionEnabled = $state(false);
  let settingsCompactionModel = $state('');
  let settingsCompactionContextWindow = $state('');
  let settingsCompactionSummaryLength = $state('');

  // Every known param for the connection's backend type (see
  // $lib/llmParamSchemas -- a fixed, per-protocol list, not an open-ended
  // set), shown as one searchable list. Values are kept as plain strings
  // here; parseParamValue() does the type-aware conversion back on save.
  let settingsParamValues = $state<Record<string, string>>({});
  let settingsParamSearch = $state('');
  // Keyed by spec.key -- set while a type: 'json' textarea holds invalid JSON.
  let settingsParamJsonErrors = $state<Record<string, string>>({});

  const knownParamSpecs = $derived(settingsConn ? getParamSpecs(settingsConn.backend_type, settingsConn.purpose) : []);
  const filteredParamRows = $derived.by(() => {
    const q = settingsParamSearch.trim().toLowerCase();
    if (!q) return knownParamSpecs;
    return knownParamSpecs.filter((r) => r.key.toLowerCase().includes(q) || r.label.toLowerCase().includes(q));
  });

  // Informational only -- leaving a field blank always omits the key entirely
  // (see handleSaveSettings) so the provider applies its own default; this
  // just tells the admin what that default is, it never pre-fills the value.
  function unsetHint(spec: { default?: unknown }, base: string): string {
    return spec.default !== undefined ? `${base} (default: ${spec.default})` : base;
  }

  function openSettings(c: Connection) {
    settingsConn = c;
    settingsBaseUrl = c.base_url;
    settingsApiKey = '';
    settingsApiKeyVisible = false;
    settingsModel = c.model;

    const values: Record<string, string> = {};
    for (const spec of getParamSpecs(c.backend_type, c.purpose)) {
      if (spec.type === 'object') {
        const nested = (c.params?.[spec.key] as Record<string, unknown> | undefined) ?? {};
        for (const field of spec.fields ?? []) {
          values[`${spec.key}.${field.key}`] = paramValueToString(nested[field.key]);
        }
      } else if (spec.type === 'json') {
        const v = c.params?.[spec.key];
        values[spec.key] = v === undefined ? '' : JSON.stringify(v, null, 2);
      } else {
        values[spec.key] = paramValueToString(c.params?.[spec.key]);
      }
    }
    settingsParamValues = values;
    settingsParamSearch = '';
    settingsParamJsonErrors = {};

    settingsCompactionEnabled = c.compaction_enabled;
    settingsCompactionModel = c.compaction_model ?? c.model;
    settingsCompactionContextWindow = c.compaction_context_window != null ? String(c.compaction_context_window) : '';
    settingsCompactionSummaryLength = c.compaction_summary_length != null ? String(c.compaction_summary_length) : '';

    settingsModels = [];
    settingsModelsError = null;
    settingsError = null;
    settingsOpen = true;
  }

  async function fetchSettingsModels() {
    if (!settingsConn) return;
    settingsModelsLoading = true;
    settingsModelsError = null;
    try {
      const res = await fetch(`/api/admin/llm-connections/${settingsConn.id}/models`);
      const d = await res.json();
      if (!res.ok || d.ok === false) {
        settingsModelsError = d.error ?? 'Failed to fetch models.';
        settingsModels = [];
      } else {
        settingsModels = d.models ?? [];
      }
    } catch (e: any) {
      settingsModelsError = e.message ?? 'Failed to fetch models.';
      settingsModels = [];
    } finally {
      settingsModelsLoading = false;
    }
  }

  async function handleSaveSettings() {
    if (!settingsConn || !settingsBaseUrl.trim()) return;
    settingsError = null;
    settingsPhase = 'testing';
    try {
      const params: Record<string, unknown> = {};
      const jsonErrors: Record<string, string> = {};
      for (const spec of knownParamSpecs) {
        if (spec.type === 'object') {
          const built = buildObjectParam(spec, settingsParamValues);
          if (built !== undefined) params[spec.key] = built;
          continue;
        }
        if (spec.type === 'json') {
          const { value, error } = parseJsonParam(settingsParamValues[spec.key] ?? '');
          if (error) {
            jsonErrors[spec.key] = error;
            continue;
          }
          if (value !== undefined) params[spec.key] = value;
          continue;
        }
        const raw = settingsParamValues[spec.key];
        if (!raw || raw.trim() === '') continue;
        const parsed = parseParamValue(spec.type, raw);
        if (parsed === undefined) continue;
        if (Array.isArray(parsed) && parsed.length === 0) continue;
        params[spec.key] = parsed;
      }

      settingsParamJsonErrors = jsonErrors;
      if (Object.keys(jsonErrors).length > 0) {
        settingsError = 'Fix invalid JSON in the highlighted parameter(s) before saving.';
        return;
      }

      const compactionContextWindow = settingsCompactionContextWindow.trim() ? parseInt(settingsCompactionContextWindow, 10) : null;
      const compactionSummaryLength = settingsCompactionSummaryLength.trim() ? parseInt(settingsCompactionSummaryLength, 10) : null;
      if (
        settingsCompactionEnabled &&
        compactionContextWindow !== null &&
        compactionSummaryLength !== null &&
        compactionSummaryLength >= compactionContextWindow
      ) {
        settingsError = 'Compaction summary length must be less than the context window.';
        return;
      }

      const testRes = await fetch('/api/admin/llm-connections/test', {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          backend_type: settingsConn.backend_type,
          base_url: settingsBaseUrl.trim(),
          api_key: settingsApiKey.trim() || null,
          connection_id: settingsConn.id,
        }),
      });
      const testData = await testRes.json().catch(() => ({}));
      if (!testRes.ok || testData.ok === false) {
        throw new Error(testData.error ?? testData.detail ?? 'Could not connect to this backend.');
      }

      settingsPhase = 'saving';
      const res = await fetch(`/api/admin/llm-connections/${settingsConn.id}`, {
        method: 'PUT',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({
          base_url: settingsBaseUrl.trim(),
          api_key: settingsApiKey.trim() || null,
          model: settingsModel.trim(),
          params,
          compaction_enabled: settingsCompactionEnabled,
          compaction_model: settingsCompactionModel.trim() || null,
          compaction_context_window: compactionContextWindow,
          compaction_summary_length: compactionSummaryLength,
        }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      addToast('Connection updated.', 'success');
      settingsOpen = false;
      await invalidateAll();
    } catch (e: any) {
      settingsError = e.message ?? 'Failed to save.';
    } finally {
      settingsPhase = null;
    }
  }

  async function handleDeleteSettings() {
    if (!settingsConn) return;
    const res = await fetch(`/api/admin/llm-connections/${settingsConn.id}`, { method: 'DELETE' });
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      throw new Error(d.detail ?? 'Failed to delete connection.');
    }
    settingsOpen = false;
    await invalidateAll();
  }

  // A purpose can have several connections; this activates one of them
  // (deactivating any siblings) and rewires the purpose's live service to it.
  async function handleActivate(c: Connection) {
    const res = await fetch(`/api/admin/llm-connections/${c.id}/activate`, { method: 'POST' });
    if (!res.ok) {
      const d = await res.json().catch(() => ({}));
      addToast(d.detail ?? 'Failed to activate connection.', 'error');
      return;
    }
    addToast('Connection activated.', 'success');
    await invalidateAll();
  }
</script>

{#snippet connectionTable(rows: Connection[])}
  <div class="table-container">
    <table class="data-table">
      <tbody>
        {#if rows.length === 0}
          <tr><td colspan="5" class="loading-cell">No connections configured.</td></tr>
        {:else}
          {#each rows as c}
            <tr>
              <td class="muted">{c.base_url}</td>
              <td class="label">{c.label}</td>
              <td class="muted">{c.has_api_key ? 'API key set' : '—'}</td>
              <td class="status-cell">
                {#if c.is_active}
                  <span class="active-badge">Active</span>
                {:else}
                  <button class="activate-btn" onclick={() => handleActivate(c)}>Activate</button>
                {/if}
              </td>
              <td class="actions-cell">
                <button class="icon-btn" title="Settings" onclick={() => openSettings(c)}>
                  <SettingsIcon />
                </button>
              </td>
            </tr>
          {/each}
        {/if}
      </tbody>
    </table>
  </div>
{/snippet}

<div class="admin-content">
  <h1 class="title">Connections</h1>

  <div class="section-header">
    <h3>Manage Ollama API Connections</h3>
    <button class="icon-btn" title="Add connection" onclick={() => openAddConnection('ollama')}>
      <PlusLgIcon />
    </button>
  </div>
  {@render connectionTable(ollamaConnections)}

  <div class="section-header">
    <h3>Manage OpenAI API Connections</h3>
    <button class="icon-btn" title="Add connection" onclick={() => openAddConnection('openai')}>
      <PlusLgIcon />
    </button>
  </div>
  {@render connectionTable(openaiConnections)}

    <div class="section-header">
    <h3>Manage Qdrant API Connections</h3>
    <button class="icon-btn" title="Add connection" onclick={() => openAddConnection('qdrant')}>
      <PlusLgIcon />
    </button>
  </div>
  {@render connectionTable(qdrantConnections)}
</div>

<!-- ── Add connection modal ──────────────────────────────────────────────── -->
<Modal title="Add Connection" open={addModalOpen} onClose={() => (addModalOpen = false)}>
  <div class="form-stack">
    <label class="field">
      <span>Purpose <span class="req">*</span></span>
      <select bind:value={addPurpose}>
        <option value="" disabled>Select a purpose…</option>
        {#each purposesFor(addBackendType) as p}
          <option value={p.key}>{p.label}</option>
        {/each}
      </select>
    </label>
    <label class="field">
      <span>Base URL <span class="req">*</span></span>
      <input type="text" bind:value={addBaseUrl} placeholder={addBackendType === 'ollama' ? 'http://localhost:11434' : addBackendType === 'qdrant' ? 'http://localhost:6333' : 'https://api.openai.com'} />
    </label>
    <label class="field">
      <span>API key</span>
      <div class="password-row">
        <input type={addApiKeyVisible ? 'text' : 'password'} bind:value={addApiKey} placeholder="optional" />
        <button type="button" class="icon-btn" title={addApiKeyVisible ? 'Hide' : 'Show'} onclick={() => (addApiKeyVisible = !addApiKeyVisible)}>
          <ShowIcon />
        </button>
      </div>
    </label>
    {#if addError}<div class="field-error">{addError}</div>{/if}
  </div>
  <svelte:fragment slot="footer">
    <button class="action-btn" onclick={handleAddConnection} disabled={addPhase !== null || !addPurpose || !addBaseUrl.trim()}>
      {addPhase === 'testing' ? 'Testing…' : addPhase === 'creating' ? 'Creating…' : 'Create'}
    </button>
  </svelte:fragment>
</Modal>

<!-- ── Settings modal ────────────────────────────────────────────────────── -->
<Modal title={settingsConn ? `${settingsConn.label} Settings` : 'Settings'} open={settingsOpen} onClose={() => (settingsOpen = false)} wide>
  <div class="form-stack">
    <label class="field">
      <span>Base URL <span class="req">*</span></span>
      <input type="text" bind:value={settingsBaseUrl} />
    </label>
    <label class="field">
      <span>API key <span class="hint">(leave blank to keep existing)</span></span>
      <div class="password-row">
        <input type={settingsApiKeyVisible ? 'text' : 'password'} bind:value={settingsApiKey} placeholder={settingsConn?.has_api_key ? '••••••••' : 'optional'} />
        <button type="button" class="icon-btn" title={settingsApiKeyVisible ? 'Hide' : 'Show'} onclick={() => (settingsApiKeyVisible = !settingsApiKeyVisible)}>
          <ShowIcon />
        </button>
      </div>
    </label>

    {#if settingsConn?.backend_type !== 'qdrant'}
    <label class="field">
      <span>Model</span>
      <div class="model-row">
        {#if settingsModels.length > 0}
          <select bind:value={settingsModel}>
            <option value="" disabled>Select a model…</option>
            {#each settingsModels as m}
              <option value={m}>{m}</option>
            {/each}
          </select>
        {:else}
          <input type="text" bind:value={settingsModel} placeholder="Model name" />
        {/if}
        <button class="fetch-btn" type="button" disabled={settingsModelsLoading} onclick={fetchSettingsModels}>
          {settingsModelsLoading ? 'Loading…' : 'Fetch models'}
        </button>
      </div>
      <span class="hint">Fetches against the last saved URL/API key &mdash; save first if you just changed them.</span>
      {#if settingsModelsError}<div class="field-error">{settingsModelsError}</div>{/if}
    </label>
    {/if}

    {#if settingsConn?.purpose === 'generation'}
    <div class="field">
      <label class="checkbox-row">
        <input type="checkbox" bind:checked={settingsCompactionEnabled} />
        <span>Enable auto-compaction</span>
      </label>
      <span class="hint">Automatically summarizes older conversation history once it exceeds the context window below, freeing up space for new turns.</span>

      {#if settingsCompactionEnabled}
        <div class="compaction-subfields">
          <label class="field">
            <span>Compaction model</span>
            {#if settingsModels.length > 0}
              <select bind:value={settingsCompactionModel}>
                <option value="" disabled>Select a model…</option>
                {#each settingsModels as m}
                  <option value={m}>{m}</option>
                {/each}
              </select>
            {:else}
              <input type="text" bind:value={settingsCompactionModel} placeholder="Model name" />
            {/if}
          </label>
          <label class="field">
            <span>Context window (tokens)</span>
            <input type="text" inputmode="numeric" bind:value={settingsCompactionContextWindow} placeholder="unset (falls back to the server default)" />
          </label>
          <label class="field">
            <span>Summary length (tokens)</span>
            <input type="text" inputmode="numeric" bind:value={settingsCompactionSummaryLength} placeholder="unset (falls back to the server default)" />
          </label>
        </div>
      {/if}
    </div>
    {/if}

    <details class="parameter-settings">
      <summary>Parameter settings</summary>
      <div class="field">
      <input type="text" class="param-search" bind:value={settingsParamSearch} placeholder="Search settings… (e.g. temperature, num_ctx)" />

      <div class="param-list">
        {#each filteredParamRows as row (row.key)}
          {#if row.type === 'object'}
            <div class="param-group">
              <span class="param-group-label" title={row.key}>{row.label}</span>
              {#each row.fields ?? [] as field (field.key)}
                <div class="param-row-item param-row-item--nested">
                  <label for={`param-${row.key}-${field.key}`} title={`${row.key}.${field.key}`}>{field.label}</label>
                  {#if field.type === 'boolean'}
                    <select id={`param-${row.key}-${field.key}`} bind:value={settingsParamValues[`${row.key}.${field.key}`]}>
                      <option value="">{unsetHint(field, 'Unset')}</option>
                      <option value="true">True</option>
                      <option value="false">False</option>
                    </select>
                  {:else if field.type === 'number' || field.type === 'integer'}
                    <input id={`param-${row.key}-${field.key}`} type="text" inputmode={field.type === 'integer' ? 'numeric' : 'decimal'} bind:value={settingsParamValues[`${row.key}.${field.key}`]} placeholder={unsetHint(field, 'unset')} />
                  {:else if field.type === 'string-list'}
                    <input id={`param-${row.key}-${field.key}`} type="text" bind:value={settingsParamValues[`${row.key}.${field.key}`]} placeholder={unsetHint(field, 'comma-separated, unset')} />
                  {:else}
                    <input id={`param-${row.key}-${field.key}`} type="text" bind:value={settingsParamValues[`${row.key}.${field.key}`]} placeholder={unsetHint(field, 'unset')} />
                  {/if}
                </div>
              {/each}
            </div>
          {:else if row.type === 'json'}
            <div class="param-row-item param-row-item--full">
              <label for={`param-${row.key}`} title={row.key}>{row.label}</label>
              <textarea
                id={`param-${row.key}`}
                class="param-json"
                rows="4"
                bind:value={settingsParamValues[row.key]}
                onblur={() => {
                  const { error } = parseJsonParam(settingsParamValues[row.key] ?? '');
                  settingsParamJsonErrors = { ...settingsParamJsonErrors, [row.key]: error ?? '' };
                }}
                placeholder={unsetHint(row, 'unset (JSON object)')}
              ></textarea>
              {#if settingsParamJsonErrors[row.key]}<div class="field-error">{settingsParamJsonErrors[row.key]}</div>{/if}
            </div>
          {:else}
            <div class="param-row-item">
              <label for={`param-${row.key}`} title={row.key}>{row.label}</label>
              {#if row.type === 'boolean'}
                <select id={`param-${row.key}`} bind:value={settingsParamValues[row.key]}>
                  <option value="">{unsetHint(row, 'Unset')}</option>
                  <option value="true">True</option>
                  <option value="false">False</option>
                </select>
              {:else if row.type === 'number' || row.type === 'integer'}
                <input id={`param-${row.key}`} type="text" inputmode={row.type === 'integer' ? 'numeric' : 'decimal'} bind:value={settingsParamValues[row.key]} placeholder={unsetHint(row, 'unset')} />
              {:else if row.type === 'string-list'}
                <input id={`param-${row.key}`} type="text" bind:value={settingsParamValues[row.key]} placeholder={unsetHint(row, 'comma-separated, unset')} />
              {:else}
                <input id={`param-${row.key}`} type="text" bind:value={settingsParamValues[row.key]} placeholder={unsetHint(row, 'unset')} />
              {/if}
            </div>
          {/if}
        {:else}
          <p class="hint">No settings match "{settingsParamSearch}".</p>
        {/each}
      </div>
      </div>
    </details>

    {#if settingsError}<div class="field-error">{settingsError}</div>{/if}
  </div>
  <svelte:fragment slot="footer">
    <button class="danger-btn" onclick={() => (confirmDeleteOpen = true)} disabled={settingsPhase !== null}>
      Delete
    </button>
    <button class="action-btn" onclick={handleSaveSettings} disabled={settingsPhase !== null || !settingsBaseUrl.trim()}>
      {settingsPhase === 'testing' ? 'Testing…' : settingsPhase === 'saving' ? 'Saving…' : 'Save'}
    </button>
  </svelte:fragment>
</Modal>

<ConfirmDeleteModal
  open={confirmDeleteOpen}
  title="Delete Connection"
  onClose={() => (confirmDeleteOpen = false)}
  onConfirm={handleDeleteSettings}
  successMessage="Connection deleted."
>
  <p>Permanently delete the <strong>{settingsConn?.label}</strong> connection?</p>
  {#if settingsConn && settingsConn.purpose !== 'reranking'}
    <p>This will disable {settingsConn.label.toLowerCase()} until a new connection is configured for it.</p>
  {/if}
</ConfirmDeleteModal>

<style>
.admin-content {
  flex: 1;
  overflow-y: auto;
  padding: calc(var(--spacing) * 4);
  max-width: var(--container-6xl);
  margin-inline: auto;
}

.title {
  font-size: var(--text-3xl);
  font-weight: 700;
  margin-bottom: 1rem;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 1.5rem 0 0.75rem;
}
.section-header h3 {
  font-size: var(--text-sm);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-neutral-600);
}

.icon-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.table-container {
  background: var(--color-neutral-50);
  padding: calc(var(--spacing) * 4);
  border-radius: var(--radius-2xl);
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}
.data-table td {
  padding: 0.75rem 1rem;
  border-bottom: 1px solid var(--color-neutral-200);
  text-align: left;
  vertical-align: middle;
}
.data-table tbody tr:last-child td { border-bottom: none; }

td.label { font-weight: 500; }
td.muted { color: var(--color-neutral-500); font-size: var(--text-sm); }
td.actions-cell { width: 3rem; }
td.status-cell { width: 6rem; }

.loading-cell {
  text-align: center;
  padding: 2rem;
  color: var(--color-neutral-500);
}

.action-btn {
  background: var(--color-blue-600); color: white;
  padding: 0.5rem 1rem; border-radius: var(--radius-lg);
  cursor: pointer; font-weight: 600; border: none; font-size: var(--text-sm);
}
.action-btn:hover:not(:disabled) { background: var(--color-blue-700); }
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.danger-btn {
  background: transparent;
  border: 1px solid var(--color-red-300);
  color: var(--color-red-600);
  padding: 0.5rem 1rem;
  border-radius: var(--radius-lg);
  cursor: pointer;
  font-weight: 600;
  font-size: var(--text-sm);
  margin-right: auto;
}
.danger-btn:hover:not(:disabled) { background: var(--color-red-50); }
.danger-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.active-badge {
  display: inline-block;
  background: var(--color-green-100);
  color: var(--color-green-700);
  padding: 0.25rem 0.6rem;
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  font-weight: 600;
  white-space: nowrap;
}

.activate-btn {
  background: transparent;
  border: 1px solid var(--color-blue-300);
  color: var(--color-blue-700);
  padding: 0.25rem 0.6rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--text-xs);
  font-weight: 600;
  white-space: nowrap;
}
.activate-btn:hover { background: var(--color-blue-50); }

.fetch-btn {
  background: transparent;
  border: 1px solid var(--color-neutral-300);
  color: var(--color-neutral-700);
  padding: 0.25rem 0.6rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--text-sm);
  white-space: nowrap;
}
.fetch-btn:hover:not(:disabled) { background: var(--color-neutral-100); }
.fetch-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.checkbox-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
  cursor: pointer;
}
.checkbox-row input[type="checkbox"] {
  width: 1rem;
  height: 1rem;
  cursor: pointer;
}

.compaction-subfields {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  padding: 0.75rem 0 0.25rem 0.9rem;
  margin-top: 0.25rem;
  border-left: 2px solid var(--color-neutral-200);
}

.form-stack {
  display: flex;
  flex-direction: column;
  gap: 0.875rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-neutral-700);
}
.field input[type="text"],
.field input[type="password"],
.field select {
  padding: 0.5rem 0.75rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  font-size: var(--text-sm);
  background: var(--color-white);
  font-family: inherit;
  width: 100%;
}
.field input:focus, .field select:focus {
  outline: none;
  border-color: var(--color-blue-500);
  box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-blue-500) 15%, transparent);
}

.hint { font-weight: 400; color: var(--color-neutral-400); }
.req { color: var(--color-red-500); }

.password-row, .model-row { display: flex; gap: 0.5rem; align-items: stretch; }
.password-row input, .model-row select, .model-row input { flex: 1; min-width: 0; }

.parameter-settings { display: flex; flex-direction: column; gap: 0.6rem; }
.parameter-settings summary {
  cursor: pointer; font-size: var(--text-sm); font-weight: 500;
  color: var(--color-neutral-500); user-select: none;
}
.parameter-settings summary:hover { color: var(--color-neutral-700); }
.parameter-settings .field { margin-top: 0.6rem; }

.param-search { margin-bottom: 0.25rem; }

.param-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  max-height: 18rem;
  overflow-y: auto;
  padding: 0.25rem;
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-md);
}

.param-row-item {
  display: grid;
  grid-template-columns: 1fr 10rem;
  align-items: center;
  gap: 0.4rem;
}
.param-row-item label {
  font-size: var(--text-xs);
  font-weight: 400;
  color: var(--color-neutral-600);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.param-row-item input,
.param-row-item select {
  padding: 0.3rem 0.5rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  background: var(--color-white);
  width: 100%;
}

.param-group {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
  padding: 0.5rem 0 0.5rem 0.6rem;
  border-left: 2px solid var(--color-neutral-200);
}
.param-group-label {
  font-size: var(--text-xs);
  font-weight: 600;
  color: var(--color-neutral-700);
}
.param-row-item--nested {
  grid-template-columns: 1fr 10rem;
}

.param-row-item--full {
  grid-template-columns: 1fr;
  gap: 0.3rem;
}
.param-row-item--full label {
  white-space: normal;
}

.param-json {
  padding: 0.4rem 0.5rem;
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  background: var(--color-white);
  width: 100%;
  resize: vertical;
}

.field-error {
  background: var(--color-red-100);
  color: var(--color-red-700);
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
}
</style>
