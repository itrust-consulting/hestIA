<script lang="ts">
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';
  import { page } from '$app/stores';

  import { messages } from '$lib/stores/chat';
  import { sendMessage, copyMessage, deleteMessage, retryMessage, sending, stop, type ParsedAttachment } from '$lib/chat/actions';
  import { loadConversations, openConversation } from '$lib/stores/conversations';
  import { renderWithCitations, stripThinkingPreamble } from '$lib/render/renderChatContent';

  import SideBar from '$lib/components/SideBar.svelte';
  import CitationsSidebar from '$lib/components/CitationsSidebar.svelte';
  import CitationPopover from '$lib/components/CitationPopover.svelte';
  import type { Citation } from '$lib/types';
  import { isIsmsActive, activeCorpusName } from '$lib/stores/isms';

  import { addToast } from '$lib/stores/toast';
  import Clipboard from '$lib/components/icons/clipboard.svelte';
  import Paperclip from '$lib/components/icons/paperclipIcon.svelte';
  import PlusLgIcon from '$lib/components/icons/plusLgIcon.svelte';
  import ArrowUpIcon from '$lib/components/icons/arrowUpIcon.svelte';
  import SquareFilledIcon from '$lib/components/icons/squareFilledIcon.svelte';
  import BinIcon from '$lib/components/icons/binIcon.svelte';
  import Retry from '$lib/components/icons/retry.svelte';
  import AttachmentPreviewModal from '$lib/components/modals/AttachmentPreviewModal.svelte';

  onMount(() => {
    const handler = (e: Event) => {
      const target = e.target as HTMLElement;
      if (target.matches("button.copy-btn")) {
        const encoded = target.getAttribute("data-code");
        if (!encoded) return;

        const text = decodeURIComponent(encoded);

        navigator.clipboard.writeText(text).then(() => {
          target.textContent = "Copied!";
          setTimeout(() => (target.textContent = "Copy"), 1200);
        });
      }
    };

    window.addEventListener("click", handler);
    return () => window.removeEventListener("click", handler);
  });
  onMount(() => window.addEventListener("keydown", onKey));
  onMount(async () => {
    await loadConversations();
    const cid = get(page).url.searchParams.get('cid');
    if (cid) openConversation(cid);
  });
  

  // auto-scroll to bottom when messages change
  messages.subscribe(() => {
    queueMicrotask(() => container?.scrollTo({ top: container.scrollHeight, behavior: 'smooth' }));
  });

  let input = '';
  let container: HTMLDivElement | null = null;
  let inputBarEl: HTMLDivElement | null = null;

  let attachments: ParsedAttachment[] = [];
  let dragOver = false;
  let parsing = false;
  let fileInputEl: HTMLInputElement | undefined;

  let previewOpen = false;
  let previewFilename = '';
  let previewMarkdown = '';

  let activeCitations: Citation[] | null = null;
  let trackLatestCitations = false;
  let thinkingExpanded: Record<string, boolean> = {};
  let thinkingStart: Record<string, number> = {};
  let thinkingEnd: Record<string, number> = {};

  $: for (const m of $messages) {
    if (m.role === 'assistant' && m.thinking) {
      if (!thinkingStart[m.id]) {
        thinkingStart = { ...thinkingStart, [m.id]: Date.now() };
      }
      if ((m.content || !$sending) && !thinkingEnd[m.id]) {
        thinkingEnd = { ...thinkingEnd, [m.id]: Date.now() };
      }
    }
  }

  function thinkingLabel(msgId: string): string {
    const start = thinkingStart[msgId];
    const end = thinkingEnd[msgId];
    if (start && end) {
      const secs = Math.round((end - start) / 1000);
      return `Thought for ${secs}s`;
    }
    return 'Thinking';
  }

  // When tracking is on, keep sidebar in sync with the latest assistant message's citations.
  $: if (trackLatestCitations) {
    const last = [...$messages].reverse().find(m => m.role === 'assistant');
    activeCitations = last?.citations?.length ? last.citations : [];
  }

  type CitePopover = { x: number; y: number; maxHeight: number; citations: Citation[] };
  let citePopover: CitePopover | null = null;
  let activeChip: HTMLElement | null = null;

  onMount(() => {
    function onChipClick(e: MouseEvent) {
      const chip = (e.target as Element).closest('.cite-chip');
      if (!(chip instanceof HTMLElement)) return;
      e.stopPropagation();

      if (chip === activeChip && citePopover) {
        citePopover = null;
        activeChip = null;
        return;
      }

      activeChip = chip;
      try {
        const cits = JSON.parse(chip.getAttribute('data-cites') ?? '[]') as Citation[];
        if (cits.length) {
          const rect = chip.getBoundingClientRect();
          const HALF_W = 176; // half of max-width (22rem ≈ 352px)
          const MARGIN = 10;
          const rawX = rect.left + rect.width / 2;
          const x = Math.max(HALF_W + MARGIN, Math.min(window.innerWidth - HALF_W - MARGIN, rawX));
          const maxHeight = window.innerHeight - rect.bottom - MARGIN;
          citePopover = { x, y: rect.bottom, maxHeight, citations: cits };
        }
      } catch { /* ignore */ }
    }

    function onDocClick(e: MouseEvent) {
      const t = e.target as Element;
      if (!t.closest('.cite-chip') && !t.closest('.cite-popover')) {
        citePopover = null;
        activeChip = null;
      }
    }

    window.addEventListener('click', onChipClick);
    document.addEventListener('click', onDocClick);
    return () => {
      window.removeEventListener('click', onChipClick);
      document.removeEventListener('click', onDocClick);
    };
  });

  function openAttachmentPreview(name: string, markdown: string) {
    previewFilename = name;
    previewMarkdown = markdown;
    previewOpen = true;
  }

  const SUPPORTED_EXTS = ['.docx', '.pdf', '.xlsx'];

  async function parseFiles(files: FileList | File[]) {
    const list = Array.from(files);
    const unsupported = list.filter(f => {
      const ext = '.' + f.name.split('.').pop()?.toLowerCase();
      return !SUPPORTED_EXTS.includes(ext);
    });
    if (unsupported.length) {
      addToast(`Unsupported file type: ${unsupported.map(f => f.name).join(', ')}. Accepted: .docx, .pdf, .xlsx`, 'error');
    }
    const supported = list.filter(f => {
      const ext = '.' + f.name.split('.').pop()?.toLowerCase();
      return SUPPORTED_EXTS.includes(ext);
    });
    if (!supported.length) return;

    parsing = true;
    try {
      await Promise.all(supported.map(async (file) => {
        const fd = new FormData();
        fd.append('file', file);
        const res = await fetch('/api/chat/parse', { method: 'POST', body: fd });
        if (!res.ok) throw new Error(`Parse failed (${res.status})`);
        const data = await res.json();
        if (data.markdown) {
          attachments = [...attachments, { name: file.name, markdown: data.markdown, size: file.size }];
        } else {
          addToast(`Could not parse ${file.name}`, 'error');
        }
      }));
    } catch (e: any) {
      addToast(e.message ?? 'Parse failed', 'error');
    } finally {
      parsing = false;
    }
  }

  function onDragOver(e: DragEvent) {
    e.preventDefault();
    dragOver = true;
  }

  function onDragLeave(e: DragEvent) {
    if (!inputBarEl?.contains(e.relatedTarget as Node)) dragOver = false;
  }

  async function onDrop(e: DragEvent) {
    e.preventDefault();
    dragOver = false;
    if (e.dataTransfer?.files?.length) await parseFiles(e.dataTransfer.files);
  }

  function removeAttachment(name: string) {
    attachments = attachments.filter(a => a.name !== name);
  }

  function pickFile() {
    fileInputEl?.click();
  }

  async function onFileInput(e: Event) {
    const target = e.target as HTMLInputElement;
    if (target.files?.length) await parseFiles(target.files);
    target.value = '';
  }

  function formatSize(bytes?: number): string {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  function send(){
    if (!input.trim() && !attachments.length) return;
    if (activeCitations !== null) { activeCitations = []; trackLatestCitations = true; }
    sendMessage(input, attachments);
    input = '';
    attachments = [];
  }

  function onKey(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
    if (e.key === "Escape" && get(sending)) stop();
  }

</script>

<!-- Page container -->

<AttachmentPreviewModal
  open={previewOpen}
  onClose={() => (previewOpen = false)}
  filename={previewFilename}
  markdown={previewMarkdown}
/>

<div class="flex-1 flex overflow-hidden">
  <SideBar isAdmin={$page.data.user?.permissions?.is_admin ?? false} />
  <div class="flex-1 flex-col flex overflow-hidden" style="min-width:0">
    {#if $isIsmsActive && $activeCorpusName}
      <div class="banner">
        <strong>Ask My Docs</strong>
        <p>Selected corpus: {$activeCorpusName}</p>
      </div>
    {/if}
  <!-- Messages -->
    <main class="chat-interface">
    
      <div
        bind:this={container}
        class="chatbox"
      >

        {#each $messages as m (m.id)}
            <div class="flex flex-col {m.role === 'user' ? 'items-end' : 'items-start'}">
              <!-- Thinking block: outside the bubble, above it -->
              {#if m.role === 'assistant' && (m.thinking || ($sending && m === $messages[$messages.length - 1] && !m.content))}
                {@const isOpen = thinkingExpanded[m.id] ?? false}
                <div class="thinking-block">
                  <button
                    class="thinking-summary"
                    on:click={() => thinkingExpanded[m.id] = !isOpen}
                  >
                    {thinkingLabel(m.id)} <span class="thinking-arrow" class:open={isOpen}>›</span>
                  </button>
                  {#if isOpen}
                    <div class="thinking-body">
                      {#if m.thinking}
                        {@html renderWithCitations(stripThinkingPreamble(m.thinking))}
                      {:else}
                        <span class="thinking-dots">…</span>
                      {/if}
                    </div>
                  {/if}
                </div>
              {/if}

              <div class="relative group max-w-[95%]">
                <!-- Bubble -->
                {#if m.role === 'user'}
                  {#if m.attachments?.length}
                    <div class="message-attachments">
                      {#each m.attachments as a}
                        <button
                          class="message-attachment-card"
                          class:clickable={!!a.markdown}
                          on:click={() => a.markdown && openAttachmentPreview(a.name, a.markdown)}
                          title={a.markdown ? 'Click to preview' : undefined}
                        >
                          <Paperclip />
                          <span class="attachment-filename">{a.name}</span>
                          {#if a.size}<span class="attachment-size">{formatSize(a.size)}</span>{/if}
                        </button>
                      {/each}
                    </div>
                  {/if}
                  <div class="chat-message user prose prose-invert">
                    {@html renderWithCitations(m.content)}
                  </div>
                {:else}
                  <div class="chat-message assistant prose dark:prose-invert">
                    {@html renderWithCitations(m.content, m.citations)}
                    {#if m.citations?.length}
                      <button
                        class="sources-btn"
                        on:click={() => { trackLatestCitations = false; activeCitations = m.citations ?? null; }}
                        title="View sources"
                      >
                        {m.citations.length} source{m.citations.length !== 1 ? 's' : ''}
                      </button>
                    {/if}
                  </div>
                {/if}

                <!-- Hover tools -->
                <div
                  class="
                    absolute -bottom-2 {m.role === 'user' ? 'right-0' : 'left-0'}
                    flex items-center gap-1 opacity-0 group-hover:opacity-100
                    transition-opacity
                  "
                >
                  <!-- Copy -->
                  <button
                    class="chat-hover-button"
                    aria-label="Copy message"
                    on:click={() => copyMessage(m.content)}
                    title="Copy"
                  >
                  <Clipboard />
                  </button>

                  <!-- Delete -->
                  <button
                    class="chat-hover-button"
                    aria-label="Delete message"
                    on:click={() => deleteMessage(m.id)}
                    title="Delete"
                  >
                    <BinIcon />
                  </button>

                  <!-- Retry (only for assistant messages) -->
                  {#if m.role === 'assistant'}
                    <button
                      class="chat-hover-button"
                      aria-label="Retry answer"
                      on:click={() => { if (activeCitations !== null) { activeCitations = []; trackLatestCitations = true; } retryMessage(m.id); }}
                      title="Retry"
                    >
                      <Retry />
                    </button>
                  {/if}
                </div>
              </div>

            </div>
        {/each}

      </div>
    </main>
    <div
      class="input-bar"
      class:drag-over={dragOver}
      bind:this={inputBarEl}
      on:dragover={onDragOver}
      on:dragleave={onDragLeave}
      on:drop={onDrop}
    >
      {#if dragOver}
        <div class="drop-overlay">Drop files here</div>
      {/if}

      <div class="textarea-wrapper">
        {#if attachments.length || parsing}
          <div class="attachment-chips">
            {#each attachments as a}
              <span class="attachment-chip">
                <Paperclip />{a.name}
                <button class="chip-remove" on:click={() => removeAttachment(a.name)} aria-label="Remove {a.name}">×</button>
              </span>
            {/each}
            {#if parsing}
              <span class="attachment-chip parsing">Parsing…</span>
            {/if}
          </div>
        {/if}

        <textarea
          bind:value={input}
          class="min-h-30 w-full resize-none rounded-3xl px-3 py-2 focus:ring-black"
          style="padding-left: 3rem;{(attachments.length || parsing) ? ' padding-top: 2.25rem;' : ''}"
          placeholder="Ask me anything…"
          rows="2"
          on:keydown={onKey}
        ></textarea>
      </div>

      <input
        bind:this={fileInputEl}
        type="file"
        accept=".docx,.pdf,.xlsx"
        multiple
        style="display:none"
        on:change={onFileInput}
      />

      <button class="input-action attach" on:click={pickFile} aria-label="Attach file" disabled={parsing}>
        <PlusLgIcon />
      </button>

      {#if $sending}
        <button class="input-action stop" on:click={stop} aria-label="Stop">
          <SquareFilledIcon />
        </button>
      {:else}
        <button class="input-action send" on:click={send} aria-label="Send">
          <ArrowUpIcon />
        </button>
      {/if}
    </div>
  </div>

  {#if activeCitations}
    <CitationsSidebar
      citations={activeCitations}
      onClose={() => { activeCitations = null; trackLatestCitations = false; }}
    />
  {/if}
</div>

{#if citePopover}
  <CitationPopover
    x={citePopover.x}
    y={citePopover.y}
    maxHeight={citePopover.maxHeight}
    citations={citePopover.citations}
  />
{/if}

<style>
  .banner {
    display: flex;
    flex-direction: column;
    align-items: left;

    color: var(--color-neutral-400);

    padding: 0.25rem 0.75rem;

    font-size: var(--text-md);
    font-weight: 500;

    animation: fadeInBanner 200ms ease-out;
  }

.banner strong {
  font-size: var(--text-lg);
  font-weight: 700;
  color: var(--color-neutral-400);
  margin-bottom: 0.15rem;
}

.banner p {
  margin: 0;
  font-size: var(--text-sm);
  font-weight: 400;
  color: var(--color-neutral-400);
}

  @keyframes fadeInBanner {
    from { opacity: 0; transform: translateY(-4px); }
    to   { opacity: 1; transform: translateY(0); }
  }

  .chat-interface{
      flex: 1 1;
      display: flex;
      flex-direction: column;
      margin-inline: auto;
      width: 100%;
      max-width: var(--container-6xl);
      padding-inline: calc(var(--spacing) * 4);
      overflow: hidden;
  }

  .chatbox{
      flex: 1 1 auto;
      overflow-y: auto;
      margin-top: calc(var(--spacing) * 4) /* 1rem = 16px */;
      padding-right: calc(var(--spacing) * 6) /* 0.75rem = 12px */;
      padding-left: calc(var(--spacing) * 2);
      width: 100%;
      height: calc(100vh - var(--header-height));
  }

  .chat-message{
      display: flex;
      flex-direction: column;
      margin-bottom: calc(var(--spacing) * 4);
      border-radius: var(--radius-2xl);
      padding-inline: calc(var(--spacing) * 4);
      padding-block: calc(var(--spacing) * 2);
  }

  .chat-message.user{
      font-size: var(--text-md) /* 0.875rem = 14px */;
      line-height: var(--tw-leading, var(--text-sm--line-height) /* calc(1.25 / 0.875) ≈ 1.428571 */);
      color: var(--color-white);
      background-color: var(--color-blue-600);
  }

  .message-attachments {
    display: flex;
    flex-direction: column;
    gap: 0.2rem;
    margin-bottom: 0.25rem;
    align-items: flex-end;
  }

  .message-attachment-card {
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    color: var(--color-neutral-500);
    font-size: 0.75rem;
    max-width: 18rem;
    background: none;
    border: none;
    padding: 0;
    cursor: default;
  }

  .message-attachment-card.clickable {
    cursor: pointer;
  }

  .message-attachment-card.clickable:hover .attachment-filename {
    text-decoration: underline;
    color: var(--color-blue-600);
  }

  .attachment-filename {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: var(--color-neutral-700);
    font-weight: 500;
  }

  .attachment-size {
    white-space: nowrap;
    flex-shrink: 0;
  }

  .chat-message.assistant{
      font-size: var(--text-md) /* 0.875rem = 14px */;
      line-height: var(--tw-leading, var(--text-sm--line-height) /* calc(1.25 / 0.875) ≈ 1.428571 */);
      color: var(--color-black);
      background-color: var(--color-neutral-100);
      max-width: none;
  }

  .input-bar {
      position: sticky;
      bottom: 0;
      z-index: 10;
      margin-inline: auto;
      width: 100%;
      max-width: var(--container-6xl);

      background: var(--color-white);
      padding-block: calc(var(--spacing) * 3);
      padding-inline: calc(var(--spacing) * 4);

      display: flex;
      gap: calc(var(--spacing) * 2);
      align-items: center;

      border-top: 1px solid var(--color-neutral-200);
  }

  .chat-hover-button{
      border-radius: 0.25rem;
      background-color: color-mix(in oklab, var(--color-black) /* #000 = #000000 */ 60%, transparent);
      color: var(--color-white); 
      padding: calc(var(--spacing) * 1);
  }

  .chat-hover-button:hover{
      background-color: color-mix(in oklab, var(--color-black) /* #000 = #000000 */ 80%, transparent);
  }


  .input-action {
    position: absolute;
    right: 1.5rem;   /* distance from right inside textarea */
    bottom: 1.5rem;  /* distance from bottom inside textarea */

    width: 34px;
    height: 34px;
    border-radius: 9999px;

    display: flex;
    align-items: center;
    justify-content: center;

    border: none;
    cursor: pointer;
    color: white;
    font-size: 1rem;

    transition: background 120ms ease, transform 120ms ease;
  }

  /* attach state */
  .input-action.attach {
    right: auto;
    left: 1.5rem;
    background: transparent;
    color: var(--color-neutral-400);
    border: 1.5px solid var(--color-neutral-300);
  }
  .input-action.attach:hover:not(:disabled) {
    color: var(--color-blue-600);
    border-color: var(--color-blue-400);
    transform: scale(1.1);
  }
  .input-action.attach:disabled {
    opacity: 0.4;
    cursor: default;
  }

  /* send state */
  .input-action.send {
    background: var(--color-blue-600);
  }
  .input-action.send:hover {
    background: var(--color-blue-700);
    transform: scale(1.1);
  }

  /* stop state */
  .input-action.stop {
    background: var(--color-blue-600);
  }
  .input-action.stop:hover {
    background: var(--color-blue-700);
    transform: scale(1.1);
  }

  .input-bar.drag-over {
    border-color: var(--color-blue-500);
    background: color-mix(in oklab, var(--color-blue-50) 60%, var(--color-white));
  }

  .drop-overlay {
    position: absolute;
    inset: 0;
    z-index: 20;
    display: flex;
    align-items: center;
    justify-content: center;
    border: 2px dashed var(--color-blue-500);
    border-radius: 0.75rem;
    background: color-mix(in oklab, var(--color-blue-50) 80%, transparent);
    color: var(--color-blue-600);
    font-size: var(--text-lg);
    font-weight: 600;
    pointer-events: none;
  }

  .textarea-wrapper {
    position: relative;
    flex: 1;
    min-width: 0;
  }

  .attachment-chips {
    position: absolute;
    top: 0.5rem;
    right: 0.75rem;
    z-index: 1;
    display: flex;
    flex-wrap: wrap;
    gap: 0.25rem;
    justify-content: flex-end;
    max-width: 85%;
    pointer-events: none;
  }

  .attachment-chip {
    display: inline-flex;
    align-items: center;
    gap: 0.25rem;
    padding: 0.2rem 0.6rem;
    border-radius: 9999px;
    background: var(--color-blue-100);
    color: var(--color-blue-700);
    font-size: var(--text-xs, 0.75rem);
    font-weight: 500;
    pointer-events: auto;
  }

  .attachment-chip.parsing {
    background: var(--color-neutral-200);
    color: var(--color-neutral-500);
    animation: pulse 1.2s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
  }

  .chip-remove {
    line-height: 1;
    font-size: 1rem;
    color: var(--color-blue-500);
    cursor: pointer;
    padding: 0;
    background: none;
    border: none;
  }

  .chip-remove:hover {
    color: var(--color-blue-800);
  }

  :global(.cite-chip) {
    display: inline-flex;
    align-items: center;
    gap: 0.2rem;
    padding: 0.15rem 0.55rem;
    border-radius: 999px;
    background: var(--color-blue-50);
    color: var(--color-blue-700);
    font-size: var(--text-xs, 0.75rem);
    font-weight: 600;
    letter-spacing: 0.03em;
    position: relative;
    cursor: pointer;
    vertical-align: baseline;
    user-select: none;
  }

  :global(.cite-chip:hover) {
    background: var(--color-blue-100);
  }

  .sources-btn {
    display: inline-flex;
    align-items: center;
    align-self: flex-start;
    gap: 0.3rem;
    margin-top: 0.6rem;
    padding: 0.2rem 0.6rem;
    border-radius: 999px;
    background: var(--color-blue-50);
    color: var(--color-blue-600);
    font-size: var(--text-xs, 0.75rem);
    font-weight: 600;
    border: 1px solid var(--color-blue-200);
    cursor: pointer;
    transition: background 0.12s;
  }

  .sources-btn:hover {
    background: var(--color-blue-100);
  }

  .thinking-block {
    max-width: 95%;
    margin-bottom: 0.4rem;
  }

  .thinking-summary {
    display: flex;
    align-items: center;
    gap: 0.25rem;
    background: none;
    border: none;
    padding: 0;
    font-size: var(--text-xs, 0.75rem);
    font-weight: 600;
    color: var(--color-neutral-400);
    cursor: pointer;
    user-select: none;
  }

  .thinking-summary:hover {
    color: var(--color-neutral-600);
  }

  .thinking-arrow {
    display: inline-block;
    font-size: 0.85rem;
    line-height: 1;
    transition: transform 0.15s;
  }

  .thinking-arrow.open {
    transform: rotate(90deg);
  }

  .thinking-body {
    margin-top: 0.4rem;
    font-size: var(--text-sm, 0.875rem);
    color: var(--color-neutral-400);
    line-height: 1.55;
  }

  .thinking-dots {
    display: inline-block;
    animation: blink 1.2s step-start infinite;
    letter-spacing: 0.1em;
  }

  @keyframes blink {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0.2; }
  }
</style>