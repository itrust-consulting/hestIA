<script lang="ts">
  import { addToast } from '$lib/stores/toast';
  import SearchIcon from '$lib/components/icons/searchIcon.svelte';
  import DownloadIcon from '$lib/components/icons/downloadIcon.svelte';
  import { tooltip } from '$lib/actions/tooltip';

  const { data } = $props();

  const LEVELS = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'];

  type LogEntry = {
    ts: string;
    level: string;
    logger: string;
    request_id: string;
    msg: string;
    [key: string]: unknown;
  };

  // ── Logging settings ────────────────────────────────────────────────────
  let logLevel = $state(data.logSettings.log_level);
  let logSettingsPhase = $state<'saving' | null>(null);
  let logSettingsError = $state<string | null>(null);

  async function saveLogLevel() {
    logSettingsError = null;
    logSettingsPhase = 'saving';
    try {
      const res = await fetch('/api/admin/logs/settings', {
        method: 'PUT',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ log_level: logLevel }),
      });
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `${res.status}`);
      }
      addToast('Log level updated.', 'success');
    } catch (e: any) {
      logSettingsError = e.message ?? 'Failed to save.';
    } finally {
      logSettingsPhase = null;
    }
  }

  // ── Log inspector ────────────────────────────────────────────────────────
  let logType = $state<'system' | 'audit'>('system');
  let filterLevel = $state('');
  let search = $state('');
  let since = $state('');
  let until = $state('');
  const limit = 50;
  let offset = $state(0);

  let entries = $state<LogEntry[]>([]);
  let total = $state(0);
  let logsLoading = $state(false);
  let logsError = $state<string | null>(null);
  let expandedIndex = $state<number | null>(null);

  function buildFilterParams(): URLSearchParams {
    const params = new URLSearchParams({ log_type: logType });
    if (filterLevel) params.set('level', filterLevel);
    if (search.trim()) params.set('search', search.trim());
    if (since) params.set('since', new Date(since).toISOString());
    if (until) params.set('until', new Date(until).toISOString());
    return params;
  }

  async function fetchLogs() {
    logsLoading = true;
    logsError = null;
    expandedIndex = null;
    try {
      const params = buildFilterParams();
      params.set('limit', String(limit));
      params.set('offset', String(offset));
      const res = await fetch(`/api/admin/logs?${params.toString()}`);
      if (!res.ok) {
        const d = await res.json().catch(() => ({}));
        throw new Error(d.detail ?? `Failed to load logs (${res.status})`);
      }
      const d = await res.json();
      entries = d.entries ?? [];
      total = d.total ?? 0;
    } catch (e: any) {
      logsError = e.message ?? 'Failed to load logs.';
      entries = [];
      total = 0;
    } finally {
      logsLoading = false;
    }
  }

  function runSearch() {
    offset = 0;
    fetchLogs();
  }

  function nextPage() {
    if (offset + limit >= total) return;
    offset += limit;
    fetchLogs();
  }

  function prevPage() {
    if (offset === 0) return;
    offset = Math.max(0, offset - limit);
    fetchLogs();
  }

  function exportHref(format: 'ndjson' | 'csv') {
    const params = buildFilterParams();
    params.set('format', format);
    return `/api/admin/logs/export?${params.toString()}`;
  }

  // ── Export format menu ────────────────────────────────────────────────
  let exportMenuOpen = $state(false);

  function toggleExportMenu() {
    exportMenuOpen = !exportMenuOpen;
  }

  function closeExportMenu() {
    exportMenuOpen = false;
  }

  function handleExportMenuOutsideClick(event: MouseEvent) {
    const menu = document.querySelector('.export-menu');
    if (menu && !menu.contains(event.target as Node)) {
      exportMenuOpen = false;
    }
  }

  $effect(() => {
    if (!exportMenuOpen) return;
    document.addEventListener('click', handleExportMenuOutsideClick);
    return () => document.removeEventListener('click', handleExportMenuOutsideClick);
  });

  function formatTs(ts: string): string {
    const d = new Date(ts);
    return Number.isNaN(d.getTime()) ? ts : d.toLocaleString();
  }

  function extraFields(entry: LogEntry): [string, unknown][] {
    return Object.entries(entry).filter(([k]) => !['ts', 'level', 'logger', 'request_id', 'msg'].includes(k));
  }

  function truncate(s: string, n = 50): string {
    return s.length > n ? `${s.slice(0, n)}…` : s;
  }

  fetchLogs();
</script>

<div class="admin-content">
  <h1 class="title">Logging</h1>

  <div class="section-header"><h3>Logging Settings</h3></div>
  <div class="panel">
    <div class="form-stack">
      <label class="field">
        <span>Log level <span class="hint">&mdash; takes effect immediately, does not persist across a restart (reverts to the LOG_LEVEL env var)</span></span>
        <select bind:value={logLevel}>
          {#each LEVELS as lvl}
            <option value={lvl}>{lvl}</option>
          {/each}
        </select>
      </label>
      {#if logSettingsError}<div class="field-error">{logSettingsError}</div>{/if}
      <div>
        <button class="action-btn" onclick={saveLogLevel} disabled={logSettingsPhase !== null}>
          {logSettingsPhase === 'saving' ? 'Saving…' : 'Save'}
        </button>
      </div>
    </div>
  </div>

  <div class="section-header"><h3>Log Inspector</h3></div>
  <div class="panel">
    <div class="filter-row">
      <label class="field">
        <span>Log type</span>
        <select bind:value={logType}>
          <option value="system">System</option>
          <option value="audit">Audit</option>
        </select>
      </label>
      <label class="field">
        <span>Min level</span>
        <select bind:value={filterLevel}>
          <option value="">All levels</option>
          {#each LEVELS as lvl}
            <option value={lvl}>{lvl}+</option>
          {/each}
        </select>
      </label>
    </div>
    <div class="filter-row">
      <label class="field">
        <span>Search</span>
        <input type="text" bind:value={search} placeholder="message or logger contains…" onkeydown={(e) => e.key === 'Enter' && runSearch()} />
      </label>
    </div>
    <div class="filter-row">
      <label class="field">
        <span>Since</span>
        <input type="datetime-local" bind:value={since} />
      </label>
      <label class="field">
        <span>Until</span>
        <input type="datetime-local" bind:value={until} />
      </label>
      <div class="filter-actions">
        <button class="icon-btn" aria-label="Search" use:tooltip={logsLoading ? 'Loading…' : 'Search'} onclick={runSearch} disabled={logsLoading}>
          <SearchIcon />
        </button>
        <div class="export-menu">
          <button class="icon-btn" aria-label="Export logs" use:tooltip={"Export"} onclick={toggleExportMenu}>
            <DownloadIcon />
          </button>
          {#if exportMenuOpen}
            <div class="user-dropdown">
              <a class="dropdown-btn" href={exportHref('ndjson')} onclick={closeExportMenu}>NDJSON</a>
              <a class="dropdown-btn" href={exportHref('csv')} onclick={closeExportMenu}>CSV</a>
            </div>
          {/if}
        </div>
      </div>
    </div>

    {#if logsError}<div class="field-error">{logsError}</div>{/if}

    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>Time</th>
            <th>Level</th>
            <th>Logger</th>
            <th>Request</th>
            <th>Message</th>
          </tr>
        </thead>
        <tbody>
          {#if entries.length === 0}
            <tr><td colspan="5" class="loading-cell">{logsLoading ? 'Loading…' : 'No log entries match these filters.'}</td></tr>
          {:else}
            {#each entries as entry, i}
              <tr class="log-row" class:log-row--expanded={expandedIndex === i} onclick={() => (expandedIndex = expandedIndex === i ? null : i)}>
                <td class="muted mono">{formatTs(entry.ts)}</td>
                <td><span class={`level-badge level-${entry.level.toLowerCase()}`}>{entry.level}</span></td>
                <td class="mono">{entry.logger}</td>
                <td class="muted mono">{entry.request_id}</td>
                <td title={entry.msg}>{truncate(entry.msg)}</td>
              </tr>
              {#if expandedIndex === i}
                <tr class="log-detail-row">
                  <td colspan="5">
                    <div class="detail-block">
                      <span class="static-label">Message</span>
                      <pre class="log-detail">{entry.msg}</pre>
                    </div>
                    {#if extraFields(entry).length > 0}
                      <div class="detail-block">
                        <span class="static-label">Fields</span>
                        <pre class="log-detail">{JSON.stringify(Object.fromEntries(extraFields(entry)), null, 2)}</pre>
                      </div>
                    {:else}
                      <span class="hint">No additional fields.</span>
                    {/if}
                  </td>
                </tr>
              {/if}
            {/each}
          {/if}
        </tbody>
      </table>
    </div>

    <div class="pager">
      <button class="fetch-btn" onclick={prevPage} disabled={offset === 0 || logsLoading}>Prev</button>
      <span class="hint">{total === 0 ? '0' : `${offset + 1}–${Math.min(offset + limit, total)}`} of {total}</span>
      <button class="fetch-btn" onclick={nextPage} disabled={offset + limit >= total || logsLoading}>Next</button>
    </div>
  </div>
</div>

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

.section-header { margin: 1.5rem 0 0.75rem; }
.section-header h3 {
  font-size: var(--text-sm);
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--color-neutral-600);
}

.panel {
  background: var(--color-neutral-50);
  padding: calc(var(--spacing) * 4);
  border-radius: var(--radius-2xl);
  box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}

.form-stack { display: flex; flex-direction: column; gap: 0.875rem; }

.field {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: var(--text-sm);
  font-weight: 500;
  color: var(--color-neutral-700);
}
.field input, .field select {
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

.hint { font-weight: 400; color: var(--color-neutral-400); font-size: var(--text-xs); }

.field-row { display: flex; gap: 2rem; flex-wrap: wrap; }
.field-static { font-size: var(--text-sm); color: var(--color-neutral-700); }
.static-label { font-weight: 600; margin-right: 0.4rem; color: var(--color-neutral-500); }

.field-error {
  background: var(--color-red-100);
  color: var(--color-red-700);
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
}

.action-btn {
  background: var(--color-blue-600); color: white;
  padding: 0.5rem 1rem; border-radius: var(--radius-lg);
  cursor: pointer; font-weight: 600; border: none; font-size: var(--text-sm);
}
.action-btn:hover:not(:disabled) { background: var(--color-blue-700); }
.action-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.fetch-btn {
  background: transparent;
  border: 1px solid var(--color-neutral-300);
  color: var(--color-neutral-700);
  padding: 0.5rem 0.75rem;
  border-radius: var(--radius-md);
  cursor: pointer;
  font-size: var(--text-sm);
  white-space: nowrap;
  text-decoration: none;
  display: inline-block;
}
.fetch-btn:hover:not(:disabled) { background: var(--color-neutral-100); }
.fetch-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.filter-row {
  display: flex;
  gap: 1rem;
  align-items: flex-end;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}
.filter-row .field { min-width: 9rem; flex: 1; }
.filter-actions { display: flex; gap: 0.5rem; align-items: center; }
.export-menu { position: relative; }

.table-container {
  background: var(--color-white);
  border: 1px solid var(--color-neutral-200);
  border-radius: var(--radius-lg);
  max-height: 32rem;
  overflow-y: auto;
}

.data-table { width: 100%; border-collapse: collapse; font-size: var(--text-sm); }
.data-table thead th {
  position: sticky; top: 0;
  background: var(--color-neutral-100);
  text-align: left;
  padding: 0.5rem 0.75rem;
  font-size: var(--text-xs);
  text-transform: uppercase;
  letter-spacing: 0.03em;
  color: var(--color-neutral-500);
}
.data-table td {
  padding: 0.5rem 0.75rem;
  border-bottom: 1px solid var(--color-neutral-200);
  vertical-align: top;
}
.data-table tbody tr:last-child td { border-bottom: none; }

.mono { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: var(--text-xs); white-space: nowrap; }
.muted { color: var(--color-neutral-500); }

.loading-cell { text-align: center; padding: 2rem; color: var(--color-neutral-500); }

.log-row { cursor: pointer; }
.log-row:hover { background: var(--color-neutral-50); }
.log-row--expanded { background: var(--color-blue-50); }
.log-detail-row td { background: var(--color-neutral-50); padding: 0.75rem; }
.log-detail {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  font-size: var(--text-xs);
  white-space: pre-wrap;
  word-break: break-word;
  margin: 0;
}

.detail-block { display: flex; flex-direction: column; gap: 0.25rem; }
.detail-block + .detail-block { margin-top: 0.75rem; }

.level-badge {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: var(--radius-md);
  font-size: var(--text-xs);
  font-weight: 600;
}
.level-debug { background: var(--color-neutral-200); color: var(--color-neutral-700); }
.level-info { background: var(--color-blue-100); color: var(--color-blue-700); }
.level-warning { background: color-mix(in oklab, orange 20%, white); color: #92400e; }
.level-error, .level-critical { background: var(--color-red-100); color: var(--color-red-700); }

.pager {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 0.75rem;
}
</style>
