<script lang="ts">
  import type { ChatMessage, Citation } from '$lib/types';
  import { renderWithCitations, stripThinkingPreamble } from '$lib/render/renderChatContent';
  import Clipboard from '$lib/components/icons/clipboard.svelte';
  import Paperclip from '$lib/components/icons/paperclipIcon.svelte';
  import BinIcon from '$lib/components/icons/binIcon.svelte';
  import Retry from '$lib/components/icons/retry.svelte';
  import { tooltip } from '$lib/actions/tooltip';

  let {
    message,
    isLast,
    sending,
    thinkingOpen,
    thinkingLabelText,
    onToggleThinking,
    onCopy,
    onDelete,
    onRetry,
    onOpenAttachment,
    onViewSources
  }: {
    message: ChatMessage;
    isLast: boolean;
    sending: boolean;
    thinkingOpen: boolean;
    thinkingLabelText: string;
    onToggleThinking: () => void;
    onCopy: () => void;
    onDelete: () => void;
    onRetry: () => void;
    onOpenAttachment: (name: string, markdown: string) => void;
    onViewSources: (citations: Citation[]) => void;
  } = $props();

  function formatSize(bytes?: number): string {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }
</script>

<div class="flex flex-col {message.role === 'user' ? 'items-end' : 'items-start'}">
  <!-- Thinking block: outside the bubble, above it -->
  {#if message.role === 'assistant' && (message.thinking || (sending && isLast && !message.content))}
    <div class="thinking-block">
      <button class="thinking-summary" on:click={onToggleThinking}>
        {thinkingLabelText} <span class="thinking-arrow" class:open={thinkingOpen}>›</span>
      </button>
      {#if thinkingOpen}
        <div class="thinking-body">
          {#if message.thinking}
            {@html renderWithCitations(stripThinkingPreamble(message.thinking))}
          {:else}
            <span class="thinking-dots">…</span>
          {/if}
        </div>
      {/if}
    </div>
  {/if}

  <div class="relative group max-w-[95%]">
    <!-- Bubble -->
    {#if message.role === 'user'}
      {#if message.images?.length}
        <div class="message-images">
          {#each message.images as src}
            <a href={src} target="_blank" rel="noopener noreferrer">
              <img {src} alt="attached image" class="message-image-thumb" />
            </a>
          {/each}
        </div>
      {/if}
      {#if message.attachments?.length}
        <div class="message-attachments">
          {#each message.attachments as a}
            <button
              class="message-attachment-card"
              class:clickable={!!a.markdown}
              on:click={() => a.markdown && onOpenAttachment(a.name, a.markdown)}
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
        {@html renderWithCitations(message.content)}
      </div>
    {:else}
      <div class="chat-message assistant prose dark:prose-invert">
        {@html renderWithCitations(message.content, message.citations)}
        {#if message.citations?.length}
          <button
            class="sources-btn"
            on:click={() => onViewSources(message.citations ?? [])}
            title="View sources"
          >
            {message.citations.length} source{message.citations.length !== 1 ? 's' : ''}
          </button>
        {/if}
        {#if message.stopped}
          <div class="stopped-note">Generation stopped.</div>
        {/if}
      </div>
    {/if}

    <!-- Hover tools -->
    <div
      class="
        absolute -bottom-2 {message.role === 'user' ? 'right-0' : 'left-0'}
        flex items-center gap-1 opacity-0 group-hover:opacity-100
        transition-opacity
      "
    >
      <!-- Copy -->
      <button class="chat-hover-button" aria-label="Copy message" on:click={onCopy} use:tooltip={"Copy"}>
        <Clipboard />
      </button>

      <!-- Delete -->
      <button class="chat-hover-button" aria-label="Delete message" on:click={onDelete} use:tooltip={"Delete"}>
        <BinIcon />
      </button>

      <!-- Retry (only for assistant messages) -->
      {#if message.role === 'assistant'}
        <button class="chat-hover-button" aria-label="Retry answer" on:click={onRetry} use:tooltip={"Retry"}>
          <Retry />
        </button>
      {/if}
    </div>
  </div>
</div>

<style>
  .chat-message {
    display: flex;
    flex-direction: column;
    margin-bottom: calc(var(--spacing) * 4);
    border-radius: var(--radius-2xl);
    padding-inline: calc(var(--spacing) * 4);
    padding-block: calc(var(--spacing) * 2);
  }

  .chat-message.user {
    font-size: var(--text-md);
    line-height: var(--tw-leading, var(--text-sm--line-height));
    color: var(--color-white);
    background-color: var(--color-blue-600);
  }

  .message-images {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-bottom: 0.3rem;
    justify-content: flex-end;
  }

  .message-image-thumb {
    max-height: 120px;
    max-width: 200px;
    border-radius: 0.5rem;
    object-fit: cover;
    cursor: pointer;
    transition: opacity 0.12s;
  }

  .message-image-thumb:hover {
    opacity: 0.85;
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

  .chat-message.assistant {
    font-size: var(--text-md);
    line-height: var(--tw-leading, var(--text-sm--line-height));
    color: var(--color-black);
    background-color: var(--color-neutral-100);
    max-width: none;
  }

  .chat-hover-button {
    border-radius: 0.25rem;
    background-color: color-mix(in oklab, var(--color-black) 60%, transparent);
    color: var(--color-white);
    padding: calc(var(--spacing) * 1);
  }

  .chat-hover-button:hover {
    background-color: color-mix(in oklab, var(--color-black) 80%, transparent);
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

  .stopped-note {
    margin-top: 0.5rem;
    font-size: var(--text-xs, 0.75rem);
    font-style: italic;
    color: var(--color-neutral-400);
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
