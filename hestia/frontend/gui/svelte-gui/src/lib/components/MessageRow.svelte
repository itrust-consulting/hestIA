<script lang="ts">
  export let item;

  import { copyMessage, deleteMessage, retryMessage } from '$lib/chat/actions';
  import { renderChatContent } from '$lib/render/renderChatContent';
</script>

<div class="flex flex-col gap-1 w-full">

  <div
    class="text-xs text-neutral-500
           {item.role === 'user' ? 'self-end pr-2' : 'self-start pl-2'}"
  >
    {new Date(item.createdAt).toLocaleTimeString()}
  </div>

    <div class="flex {item.role === 'user' ? 'justify-end' : 'justify-start'}">
        <div class="relative group max-w-[95%]">
        {#if item.role === 'user'}
            <div class="rounded-2xl bg-blue-600 text-white px-4 py-2 shadow-sm text-sm">
            {@html renderChatContent(item.content)}
            </div>
        {/if}
        {#if item.role === 'assistant'}
            <div class="rounded-2xl bg-neutral-100 dark:bg-neutral-800
                        px-4 py-2 shadow-sm prose prose-sm dark:prose-invert max-w-none">
            {@html renderChatContent(item.content)}
            </div>
        {/if}
        <div class="absolute -top-2 -right-2
                    opacity-0 group-hover:opacity-100
                    transition-opacity flex gap-1">
            
            <!-- Copy -->
            <button
                class="rounded bg-black/60 text-white p-1 hover:bg-black/80"
                aria-label="Copy message"
                on:click={() => copyMessage(item.content)}
                title="Copy"
            >
                <!-- copy icon (heroicons) -->
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
                    fill="none" stroke="currentColor" stroke-width="1.8"
                    class="w-4 h-4">
                <path stroke-linecap="round" stroke-linejoin="round"
                        d="M8 7H6a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h9a2 2 0 0 0 2-2v-2M15 3h2a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2h-2M15 3H8a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h7M15 3v2"/>
                </svg>
            </button>

            <!-- Delete -->
            <button
                class="rounded bg-black/60 text-white p-1 hover:bg-black/80"
                aria-label="Delete message"
                on:click={() => deleteMessage(item.id)}
                title="Delete"
            >
                <!-- trash icon -->
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
                    fill="none" stroke="currentColor" stroke-width="1.8"
                    class="w-4 h-4">
                <path stroke-linecap="round" stroke-linejoin="round"
                        d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/>
                </svg>
            </button>

            <!-- Retry (only for assistant messages) -->
            {#if item.role === 'assistant'}
                <button
                class="rounded bg-black/60 text-white p-1 hover:bg-black/80"
                aria-label="Retry answer"
                on:click={() => retryMessage(item.id)}
                title="Retry"
                //disabled={sending}
                >
                <!-- refresh icon -->
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"
                    fill="none" stroke="currentColor" stroke-width="1.8"
                    class="w-4 h-4">
                    <path stroke-linecap="round" stroke-linejoin="round"
                        d="M4 4v6h6M20 20v-6h-6M20 8a8 8 0 1 0-6.906 11.853"/>
                </svg>
                </button>
            {/if}
        </div>
        </div>
    </div>
</div>