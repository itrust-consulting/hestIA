<script lang="ts">
  import { onMount } from 'svelte';
  import { get } from 'svelte/store';

  import { messages } from '$lib/stores/chat';
  import { sendMessage, copyMessage, deleteMessage, retryMessage, sending, stop } from '$lib/chat/actions';
  import { loadConversations } from '$lib/stores/conversations';
  import { renderChatContent } from '$lib/render/renderChatContent';

  import SideBar from '$lib/components/SideBar.svelte';
  import { isIsmsActive, activeCorpusName } from '$lib/stores/isms';

  import Clipboard from '$lib/components/icons/clipboard.svelte';
  import BinIcon from '$lib/components/icons/binIcon.svelte';
  import Retry from '$lib/components/icons/retry.svelte';

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
  onMount(() => {loadConversations();});
  

  // auto-scroll to bottom when messages change
  messages.subscribe(() => {
    queueMicrotask(() => container?.scrollTo({ top: container.scrollHeight, behavior: 'smooth' }));
  });

  let input = '';
  let container: HTMLDivElement | null = null;

  function send(){
    sendMessage(input);
    input = '';
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

<div class="flex-1 flex overflow-hidden">
  <SideBar />
  <div class="flex-1 flex-col flex overflow-hidden">
    {#if $isIsmsActive && $activeCorpusName}
      <div class="banner">
        <strong>ISMS active</strong>
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
            <div class="flex {m.role === 'user' ? 'justify-end' : 'justify-start'}">
              <div class="relative group max-w-[95%]">
                <!-- Bubble -->
                {#if m.role === 'user'}
                  <div class="chat-message user">
                    {@html renderChatContent(m.content)}
                  </div>
                {:else}
                  <div class="chat-message assistant prose">
                    {@html renderChatContent(m.content)}
                  </div>
                {/if}

                <!-- Hover tools -->
                <div
                  class="
                    absolute -bottom-2 ${m.role === 'user' ? '-right' : '-left'}
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
                      on:click={() => retryMessage(m.id)}
                      title="Retry"
                    >
                      <Retry />
                    </button>
                  {/if}
                </div>
              </div>
            </div>
        {/each}

        {#if $sending}
          <div class="mb-2 text-sm text-neutral-500">Thinking…</div>
        {/if}
      </div>
    </main>
    <div class="input-bar">
      <textarea
        bind:value={input}
        class="min-h-30 w-full resize-none rounded-3xl px-3 py-2 focus:ring-black"
        placeholder="Ask me anything…"
        rows="2"
        on:keydown={onKey}
      >
      </textarea>


      <!-- SEND / STOP button INSIDE the textarea -->
      {#if $sending}
        <button class="input-action stop" on:click={stop} aria-label="Stop">
          ■
        </button>
      {:else}
        <button class="input-action send" on:click={send} aria-label="Send">
          ➤
        </button>
      {/if}


    </div>
  </div>
</div>

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
  font-size: var(--text-lg);      /* bigger */
  font-weight: 700;               /* bold */
  color: var(--color-neutral-400);
  margin-bottom: 0.15rem;
}

.banner p {
  margin: 0;
  font-size: var(--text-sm);      /* smaller */
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
</style>