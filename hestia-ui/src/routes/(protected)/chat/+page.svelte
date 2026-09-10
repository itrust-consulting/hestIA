<script lang="ts">
  import { onMount, tick } from 'svelte';
  import { get } from 'svelte/store';
  import { page } from '$app/stores';
  import { VList } from 'virtua/svelte';
  import type { VListHandle } from 'virtua/svelte';

  import { messages, isMutatingFront } from '$lib/stores/chat';
  import { sendMessage, copyMessage, deleteMessage, retryMessage, sending, stop, type ParsedAttachment, type ImageAttachment } from '$lib/chat/actions';
  import {
    loadConversations, openConversation,
    hasMoreBefore, isLoadingOlder, loadOlderMessages,
    reportScrollPosition,
  } from '$lib/stores/conversations';
  import { scrollToBottomRequested } from '$lib/stores/chatScroll';

  import SideBar from '$lib/components/SideBar.svelte';
  import CitationsSidebar from '$lib/components/CitationsSidebar.svelte';
  import CitationPopover from '$lib/components/CitationPopover.svelte';
  import MessageRow from '$lib/components/MessageRow.svelte';
  import ContextUsageRing from '$lib/components/ContextUsageRing.svelte';
  import type { ChatMessage, Citation } from '$lib/types';
  import { isIsmsActive, activeCorpusId, activeCorpusName, toggleIsmsActive, requestOpenIsmsModal, selectCorpus } from '$lib/stores/isms';
  import { corpora, loadCorpora } from '$lib/stores/corpora';
  import { loadActiveModel } from '$lib/stores/generationModel';
  import ChevronIcon from '$lib/components/icons/chevronIcon.svelte';

  import { addToast } from '$lib/stores/toast';
  import Paperclip from '$lib/components/icons/paperclipIcon.svelte';
  import PlusLgIcon from '$lib/components/icons/plusLgIcon.svelte';
  import ArrowUpIcon from '$lib/components/icons/arrowUpIcon.svelte';
  import SquareFilledIcon from '$lib/components/icons/squareFilledIcon.svelte';
  import AttachmentPreviewModal from '$lib/components/modals/AttachmentPreviewModal.svelte';
  import { tooltip } from '$lib/actions/tooltip';

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
  onMount(() => {
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });
  let chatLoadError: string | null = null;

  async function loadInitialChatData() {
    chatLoadError = null;
    try {
      await loadConversations();
      const cid = get(page).url.searchParams.get('cid');
      if (cid) openConversation(cid);
    } catch (e) {
      chatLoadError = e instanceof Error ? e.message : 'Failed to load your conversations.';
    }
  }

  onMount(() => {
    loadInitialChatData();
  });
  onMount(() => {
    loadCorpora(get(page).data.user);
  });
  onMount(() => {
    loadActiveModel();
  });
  

  let vlist: VListHandle | undefined;
  let isNearBottom = true;

  function handleVListScroll(offset: number) {
    if (!vlist) return;
    const distanceFromBottom = vlist.getScrollSize() - offset - vlist.getViewportSize();
    isNearBottom = distanceFromBottom < 80;
    if (offset < 200 && get(hasMoreBefore) && !get(isLoadingOlder)) {
      loadOlderMessages();
    }
    reportScrollPosition(vlist.findItemIndex(offset));
  }

  // auto-scroll to bottom when messages change, but not while mutating the
  // front of the list (prepending older history, or evicting the head)
  // and not if the user has scrolled up to read earlier messages
  messages.subscribe(() => {
    if (get(isMutatingFront)) return;
    if (isNearBottom) {
      // no smooth behavior here: this fires on every streaming token, and
      // restarting a smooth-scroll animation that often makes it look stuck
      tick().then(() => vlist?.scrollToIndex(get(messages).length - 1, { align: 'end' }));
    }
  });

  scrollToBottomRequested.subscribe(() => {
    tick().then(() => vlist?.scrollToIndex(get(messages).length - 1, { align: 'end' }));
  });

  let input = '';
  let inputBarEl: HTMLDivElement | null = null;
  let textareaEl: HTMLTextAreaElement | undefined;

  const MAX_TEXTAREA_HEIGHT = 200; // px

  function resizeTextarea() {
    if (!textareaEl) return;
    textareaEl.style.height = 'auto';
    textareaEl.style.height = Math.min(textareaEl.scrollHeight, MAX_TEXTAREA_HEIGHT) + 'px';
  }

  let attachments: ParsedAttachment[] = [];
  let images: ImageAttachment[] = [];
  let dragOver = false;
  let parsing = false;
  let fileInputEl: HTMLInputElement | undefined;

  const IMAGE_EXTS = ['.jpg', '.jpeg', '.png', '.gif', '.webp'];

  function readAsDataURL(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.onerror = reject;
      reader.readAsDataURL(file);
    });
  }

  let previewOpen = false;
  let previewFilename = '';
  let previewMarkdown = '';

  let activeCitations: Citation[] | null = null;
  let trackLatestCitations = false;
  let thinkingExpanded: Record<string, boolean> = {};

  function thinkingLabel(m: ChatMessage, isActive: boolean): string {
    if (m.compacting && !m.thinking) return 'Compacting…';
    if (m.thinkingSecs != null) return `Thought for ${m.thinkingSecs}s`;
    return isActive ? 'Thinking' : 'Thought';
  }

  // When tracking is on, keep sidebar in sync with the latest assistant message's citations.
  $: if (trackLatestCitations) {
    const last = [...$messages].reverse().find(m => m.role === 'assistant');
    activeCitations = last?.citations?.length ? last.citations : [];
  }

  type CitePopover = { x: number; y: number; maxHeight: number; citations: Citation[] };
  let citePopover: CitePopover | null = null;
  let activeChip: HTMLElement | null = null;

  let corpusDropdownOpen = false;

  function chooseCorpus(c: { id: string; name: string }) {
    selectCorpus(c.id, c.name);
    corpusDropdownOpen = false;
  }

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
      if (corpusDropdownOpen && !t.closest('.corpus-picker')) {
        corpusDropdownOpen = false;
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

  const SUPPORTED_EXTS = ['.docx', '.pdf', '.xlsx', '.xlsm', '.json', '.csv', '.txt', '.md', '.markdown', '.pptx'];

  async function parseFiles(files: FileList | File[]) {
    const list = Array.from(files);

    const imageFiles = list.filter(f => IMAGE_EXTS.includes('.' + (f.name.split('.').pop()?.toLowerCase() ?? '')));
    const docFiles   = list.filter(f => SUPPORTED_EXTS.includes('.' + (f.name.split('.').pop()?.toLowerCase() ?? '')));
    const unsupported = list.filter(f => {
      const ext = '.' + (f.name.split('.').pop()?.toLowerCase() ?? '');
      return !IMAGE_EXTS.includes(ext) && !SUPPORTED_EXTS.includes(ext);
    });

    if (unsupported.length) {
      addToast(`Unsupported file type: ${unsupported.map(f => f.name).join(', ')}`, 'error');
    }

    if (imageFiles.length) {
      await Promise.all(imageFiles.map(async (file) => {
        const dataUrl = await readAsDataURL(file);
        images = [...images, { dataUrl, name: file.name, size: file.size }];
      }));
    }

    if (!docFiles.length) return;

    parsing = true;
    try {
      await Promise.all(docFiles.map(async (file) => {
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

  function removeImage(name: string) {
    images = images.filter(i => i.name !== name);
  }

  async function onPaste(e: ClipboardEvent) {
    const items = Array.from(e.clipboardData?.items ?? []);
    const imageItems = items.filter(i => i.type.startsWith('image/'));
    if (!imageItems.length) return;
    e.preventDefault();
    await Promise.all(imageItems.map(async (item, idx) => {
      const file = item.getAsFile();
      if (!file) return;
      const name = file.name && file.name !== 'image.png' ? file.name : `pasted-image-${images.length + idx + 1}.png`;
      const dataUrl = await readAsDataURL(file);
      images = [...images, { dataUrl, name, size: file.size }];
    }));
  }

  function pickFile() {
    fileInputEl?.click();
  }

  async function onFileInput(e: Event) {
    const target = e.target as HTMLInputElement;
    if (target.files?.length) await parseFiles(target.files);
    target.value = '';
  }

  function send(){
    if (!input.trim() && !attachments.length && !images.length) return;
    if (activeCitations !== null) { activeCitations = []; trackLatestCitations = true; }
    sendMessage(input, attachments, images);
    input = '';
    attachments = [];
    images = [];
    tick().then(resizeTextarea);
  }

  function cycleCorpus(direction: 1 | -1) {
    const list = get(corpora);
    if (!list.length) return;
    const currentId = get(activeCorpusId);
    const idx = list.findIndex(c => c.id === currentId);
    const next = list[(idx + direction + list.length) % list.length];
    selectCorpus(next.id, next.name);
  }

  // onKey is bound both on window (below) and on the textarea's own
  // keydown, so a physical keypress made while the textarea is focused
  // reaches this function twice (element phase, then bubbling to window)
  // -- both calls share the exact same KeyboardEvent instance, so this
  // dedupes by identity to avoid double-handling one keypress.
  let lastHandledIsmsEvent: KeyboardEvent | null = null;

  function onKey(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
    if (e.key === "Escape" && get(sending)) stop();
    if (e.ctrlKey && e.shiftKey && e.key.toLowerCase() === 'd') {
      e.preventDefault();
      if (e === lastHandledIsmsEvent) return;
      lastHandledIsmsEvent = e;
      if (!toggleIsmsActive()) requestOpenIsmsModal();
    }
    if (e.ctrlKey && e.shiftKey && (e.key === 'ArrowDown' || e.key === 'ArrowUp')) {
      e.preventDefault();
      if (e === lastHandledIsmsEvent) return;
      lastHandledIsmsEvent = e;
      cycleCorpus(e.key === 'ArrowDown' ? 1 : -1);
    }
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
        <div class="corpus-picker">
          <button
            type="button"
            class="corpus-picker-toggle"
            on:click={() => corpusDropdownOpen = !corpusDropdownOpen}
            aria-expanded={corpusDropdownOpen}
            aria-haspopup="listbox"
            use:tooltip={`Switch corpus<br/>Ctrl+Shift+↑ / Ctrl+Shift+↓`}
          >
            <p>Selected corpus: {$activeCorpusName}</p>
            <span class="corpus-caret" class:open={corpusDropdownOpen}><ChevronIcon /></span>
          </button>
          {#if corpusDropdownOpen}
            <ul class="corpus-dropdown" role="listbox">
              {#each $corpora as c}
                <li role="option" aria-selected={c.id === $activeCorpusId}>
                  <button type="button" class="corpus-option" class:selected={c.id === $activeCorpusId} on:click={() => chooseCorpus(c)}>
                    {c.name}
                  </button>
                </li>
              {/each}
            </ul>
          {/if}
        </div>
      </div>
    {/if}
  <!-- Messages -->
    <main class="chat-interface">

      {#if chatLoadError}
        <div class="chat-load-error">
          <p>{chatLoadError}</p>
          <button type="button" on:click={loadInitialChatData}>Retry</button>
        </div>
      {/if}

      <div class="chatbox">
        <VList
          bind:this={vlist}
          data={$messages}
          getKey={(m) => m.id}
          shift={$isMutatingFront}
          style="height: 100%; width: 100%;"
          onscroll={handleVListScroll}
        >
          {#snippet children(m, index)}
            <MessageRow
              message={m}
              isLast={index === $messages.length - 1}
              sending={$sending}
              thinkingOpen={thinkingExpanded[m.id] ?? false}
              thinkingLabelText={thinkingLabel(m, index === $messages.length - 1 && $sending)}
              onToggleThinking={() => (thinkingExpanded[m.id] = !(thinkingExpanded[m.id] ?? false))}
              onCopy={() => copyMessage(m.content)}
              onDelete={() => deleteMessage(m.id)}
              onRetry={() => { if (activeCitations !== null) { activeCitations = []; trackLatestCitations = true; } retryMessage(m.id); }}
              onOpenAttachment={openAttachmentPreview}
              onViewSources={(citations) => { trackLatestCitations = false; activeCitations = citations; }}
            />
          {/snippet}
        </VList>
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

      <div class="composer">
        <div class="textarea-wrapper">
          {#if attachments.length || images.length || parsing}
            <div class="attachment-chips">
              {#each images as img}
                <span class="attachment-chip image-chip-compose">
                  <img src={img.dataUrl} alt={img.name} class="compose-thumb" />
                  <button class="chip-remove" on:click={() => removeImage(img.name)} aria-label="Remove {img.name}" use:tooltip={`Remove ${img.name}`}>×</button>
                </span>
              {/each}
              {#each attachments as a}
                <span class="attachment-chip">
                  <Paperclip />{a.name}
                  <button class="chip-remove" on:click={() => removeAttachment(a.name)} aria-label="Remove {a.name}" use:tooltip={`Remove ${a.name}`}>×</button>
                </span>
              {/each}
              {#if parsing}
                <span class="attachment-chip parsing">Parsing…</span>
              {/if}
            </div>
          {/if}

          <textarea
            bind:this={textareaEl}
            bind:value={input}
            class="composer-textarea min-h-15 w-full resize-none px-1 py-1"
            style={(attachments.length || images.length || parsing) ? 'padding-top: 2.25rem;' : ''}
            placeholder="Ask me anything…"
            rows="2"
            on:keydown={onKey}
            on:paste={onPaste}
            on:input={resizeTextarea}
          ></textarea>
        </div>

        <input
          bind:this={fileInputEl}
          type="file"
          accept=".docx,.pdf,.xlsx,.xlsm,.json,.csv,.txt,.md,.markdown,.pptx,.jpg,.jpeg,.png,.gif,.webp"
          multiple
          style="display:none"
          on:change={onFileInput}
        />

        <div class="action-row">
          <button class="input-action attach" on:click={pickFile} aria-label="Attach file" use:tooltip={"Attach file"} disabled={parsing}>
            <PlusLgIcon />
          </button>

          <ContextUsageRing />

          {#if $sending}
            <button class="input-action stop" on:click={stop} aria-label="Stop" use:tooltip={"Stop"}>
              <SquareFilledIcon />
            </button>
          {:else}
            <button class="input-action send" on:click={send} aria-label="Send" use:tooltip={"Send"}>
              <ArrowUpIcon />
            </button>
          {/if}
        </div>
      </div>
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

.chat-load-error {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin: 0.75rem;
  padding: 0.6rem 0.9rem;
  border-radius: var(--radius-lg);
  background: var(--color-red-50, #fef2f2);
  color: var(--color-red-700, #b91c1c);
  font-size: var(--text-sm);
}

.chat-load-error p {
  margin: 0;
}

.chat-load-error button {
  flex-shrink: 0;
  padding: 0.35rem 0.9rem;
  border: 1px solid currentColor;
  border-radius: var(--radius-md, 6px);
  background: transparent;
  color: inherit;
  font-weight: 600;
  font-size: var(--text-sm);
  cursor: pointer;
}

.corpus-picker {
  position: relative;
}

.corpus-picker-toggle {
  display: flex;
  align-items: center;
  gap: 0.2rem;
  background: none;
  border: none;
  padding: 0;
  margin: 0;
  cursor: pointer;
  font: inherit;
  color: inherit;
}

.corpus-picker-toggle:hover p {
  color: var(--color-neutral-600);
}

.corpus-caret {
  display: inline-flex;
  color: var(--color-neutral-600);
  transition: transform 120ms ease;
}

.corpus-caret :global(svg) {
  width: 0.65rem;
  height: 0.65rem;
}

.corpus-caret.open {
  transform: rotate(180deg);
}

.corpus-dropdown {
  position: absolute;
  top: calc(100% + 0.25rem);
  left: 0;
  z-index: 20;
  min-width: 12rem;
  max-height: 16rem;
  overflow-y: auto;
  margin: 0;
  padding: 0.25rem;
  list-style: none;
  background: var(--color-white);
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  box-shadow: 0 4px 12px color-mix(in oklab, black 15%, transparent);
}

.corpus-option {
  display: block;
  width: 100%;
  text-align: left;
  padding: 0.375rem 0.5rem;
  border: none;
  border-radius: var(--radius-sm);
  background: none;
  font: inherit;
  font-size: var(--text-sm);
  color: var(--color-neutral-700);
  cursor: pointer;
}

.corpus-option:hover {
  background: var(--color-neutral-100);
}

.corpus-option.selected {
  font-weight: 600;
  color: var(--color-blue-700);
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
      margin-top: calc(var(--spacing) * 4) /* 1rem = 16px */;
      padding-right: calc(var(--spacing) * 6) /* 0.75rem = 12px */;
      padding-left: calc(var(--spacing) * 2);
      width: 100%;
      height: calc(100vh - var(--header-height));
  }

  .image-chip-compose {
    padding: 0.15rem 0.4rem 0.15rem 0.25rem;
    gap: 0.3rem;
  }

  .compose-thumb {
    height: 1.5rem;
    width: 1.5rem;
    border-radius: 0.25rem;
    object-fit: cover;
    flex-shrink: 0;
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

      border-top: 1px solid var(--color-neutral-200);
  }

  /* The single visible input "box" -- previously the <textarea> itself drew
     the rounded border (via rounded-3xl + the forms plugin's default ring).
     Now the box is this wrapper, split into two rows: text on top, buttons
     below, both inside the same border/rounding instead of buttons floating
     on top of the text. */
  .composer {
    display: flex;
    flex-direction: column;
    gap: calc(var(--spacing) * 2);
    border: 1px solid var(--color-neutral-300);
    border-radius: 1.5rem;
    background: var(--color-white);
    padding: calc(var(--spacing) * 3);
    transition: border-color 120ms ease;
  }
  .composer:focus-within {
    border-color: var(--color-neutral-500);
  }

  .action-row {
    display: flex;
    align-items: center;
    gap: calc(var(--spacing) * 2);
    padding-top: calc(var(--spacing) * 2);
    border-top: 1px solid var(--color-neutral-200);
  }

  .input-action {
    width: 34px;
    height: 34px;
    border-radius: 9999px;
    flex-shrink: 0;

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

  /* send state -- pushed to the far right of the action row */
  .input-action.send {
    margin-left: auto;
    background: var(--color-blue-600);
  }
  .input-action.send:hover {
    background: var(--color-blue-700);
    transform: scale(1.1);
  }

  /* stop state -- pushed to the far right of the action row */
  .input-action.stop {
    margin-left: auto;
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

  /* @tailwindcss/forms gives every textarea a default border + focus ring
     (box-shadow) -- .composer is the visible box now, so strip both here.
     max-height matches MAX_TEXTAREA_HEIGHT in the script -- resizeTextarea()
     grows .style.height up to that cap as the user types, then this
     overflow rule takes over so it scrolls internally instead of growing
     further. */
  .composer-textarea {
    border: none;
    border-radius: 0;
    background: transparent;
    box-shadow: none;
    max-height: 200px;
    overflow-y: auto;
  }
  .composer-textarea:focus {
    border: none;
    box-shadow: none;
    outline: none;
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

</style>