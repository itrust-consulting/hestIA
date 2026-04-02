<script lang="ts">
    import { writable } from 'svelte/store';
    import { tick } from 'svelte';
    import ISMSModal from './modals/ISMSModal.svelte';
    import AuditModal from './modals/AuditModal.svelte';
    import AssetModal from './modals/AssetModal.svelte';
    import { isIsmsActive } from '$lib/stores/isms';
    import SidebarLeft from './icons/sidebar-left.svelte';
    import Chaticon from './icons/chaticon.svelte';
    import BinIcon from './icons/binIcon.svelte';

    import { PUBLIC_APP_VERSION } from '$env/static/public';

    import {
        conversations,
        activeConversationId,
        startNewChat,
        openConversation,
        renameConversation,
        deleteConversation as removeConversation
    } from '$lib/stores/conversations';

    const currentVersion = PUBLIC_APP_VERSION;

    const sidebarOpen = writable<boolean>(true);
    
    let openModal: null | "isms" | "audit" | "asset" = null;

    function open(modal: "isms" | "audit" | "asset") {
        openModal = modal;
    }

    function close() {
        openModal = null;
    }

    function newChat() {
        // Save current (if any) and start a fresh chat
        startNewChat();
        // You can also collapse on small screens if you want
    }

    function deleteConversation(id: string, e: Event) {
        e.stopPropagation(); // avoid triggering "open"
        removeConversation(id);
    }

    // Inline rename state
    let editingId: string | null = null;
    let draftTitle = '';
    let inputRef: HTMLInputElement | null = null;

    async function startEdit(id: string, currentTitle: string) {
        editingId = id;
        draftTitle = currentTitle;
        await tick();            // wait for input to render
        inputRef?.focus();
        inputRef?.select();
    }

    function cancelEdit() {
        editingId = null;
        draftTitle = '';
    }

    function commitEdit() {
        if (!editingId) return;
        renameConversation(editingId, draftTitle);
        cancelEdit();
    }

    function onRowClick(id: string) {
        // If editing, don't open
        if (editingId) return;
        openConversation(id);
    }

    function onRenameKey(e: KeyboardEvent) {
        if (e.key === 'Enter') {
            e.preventDefault();
            commitEdit();
        } else if (e.key === 'Escape') {
            e.preventDefault();
            cancelEdit();
        }
    }

</script>

<aside class="sidebar" class:sidebar-closed={!$sidebarOpen} aria-label="Conversations" aria-hidden={!$sidebarOpen}>

  <div class="sidebar-header"> 
    
    <button class="new-chat-btn" onclick={newChat} title="New Chat" aria-label="New Chat">
        <Chaticon/>
        <span>New Chat</span>
    </button>

    <button
        class="sidebar-toggle"
        onclick={() => sidebarOpen.update((v) => !v)}
        aria-label="Toggle sidebar"
        aria-expanded={$sidebarOpen}
        aria-controls="sidebar-list"
        title={$sidebarOpen ? 'Collapse' : 'Expand'}
        >
        <SidebarLeft/>
    </button>
  </div>

  
    <div id="agent-list" class="agent-list" role="list">
        <p>Agents</p>
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <div class="sidebar-item agent-item" onclick={() => open("isms")}>
            ISMS
            {#if $isIsmsActive}
                <span class="active-dot"></span>
            {/if}
        </div>
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <div class="sidebar-item" onclick={() => open("audit")}>
            Audit Assitant
        </div>
        <!-- svelte-ignore a11y_no_static_element_interactions -->
        <!-- svelte-ignore a11y_click_events_have_key_events -->
        <div class="sidebar-item" onclick={() => open("asset")}>
            Asset Manager
        </div>
    </div>

    <div id="sidebar-list" class="sidebar-list" role="list">
    <p>Chats</p>
        {#each $conversations as conv}
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
            <div
            class="sidebar-item"
            class:active={$activeConversationId === conv.id}
            role="listitem"
            aria-current={$activeConversationId === conv.id ? 'true' : undefined}
            onclick={() => onRowClick(conv.id)}
            title={conv.title}
            >

            {#if editingId === conv.id}
                <input
                class="sidebar-rename"
                bind:this={inputRef}
                bind:value={draftTitle}
                onkeydown={onRenameKey}
                onblur={commitEdit}
                aria-label="Edit conversation title"
                maxlength="80"
                />
            {:else}
                <!-- svelte-ignore a11y_no_static_element_interactions -->
                <span
                class="sidebar-item__title"
                ondblclick={() => startEdit(conv.id, conv.title)}
                >
                {conv.title}
                </span>
            {/if}

            <button class="delete-btn" onclick={(e) => deleteConversation(conv.id, e)} aria-label="Delete conversation">
                <BinIcon />
            </button>
            </div>
        {/each}
    </div>
    <div class="sidebar-footer">
        <span class="version">{currentVersion}</span>
    </div>
</aside>


<ISMSModal open={openModal === "isms"} onClose={close} isAdmin={true}/>
<AuditModal open={openModal === "audit"} onClose={close} />
<AssetModal open={openModal === "asset"} onClose={close} />

<style>

    .sidebar {
        position: sticky;
        top: var(--header-height);
        height: calc(100vh - var(--header-height));
        width: 280px;         /* your expanded width */
        flex-shrink: 0;
        overflow-y: auto;
        border-right: 1px solid var(--color-neutral-200);
        background: var(--color-neutral-200);
        padding: 1rem;
        display: flex;
        flex-direction: column;
        transition: width 200ms ease, transform 200ms ease, opacity 150ms ease, padding 200ms ease;
    }


    .sidebar-toggle {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        border-radius: var(--radius-lg);
        color: var(--color-neutral-700);
        border: none;
        cursor: pointer;
        transition: background-color 150ms ease;
    }
    .sidebar-toggle:hover {
        transform: scale(1.4);
    }

    .sidebar-closed {
        width: 56px;                 
        padding: 0.75rem;            
        transform: translateX(0);    
        opacity: 1;                 
        /* IMPORTANT: allow clicks so the toggle works */
        pointer-events: auto;
    }

    .sidebar-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }


    .agent-list {
        display: flex;
        flex-direction: column;
        gap: .5rem;
    }
    .agent-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .agent-item .active-dot { /* green-500 */
        border-radius: 50%;
        margin-left: auto;
        animation: pulse 1.6s ease-in-out infinite;

        /* NEW: subtle 3D shading */
        background: radial-gradient(
            circle at 30% 30%,
            #7ef8a1,     /* highlight */
            #22c55e 60%, /* main green */
            #139b45 100% /* darker edge */
        );

        width: 15px;
        height: 15px;
    }

    @keyframes pulse {
        0% { transform: scale(1); opacity: 0.9; }
        50% { transform: scale(1.2); opacity: 1; }
        100% { transform: scale(1); opacity: 0.9; }
    }

    .sidebar-list {
        display: flex;
        flex-direction: column;
        gap: .5rem;
    }

    .sidebar-item {
        display: flex;
        align-items: center;
        justify-content: space-between;
        line-height: 1.5rem;
        height: 1.75rem;
        padding-block: 0;
        padding-inline: 1rem;
        margin-bottom: calc(var(--spacing) * .5);
        position: relative;                     /* for the accent bar */
        border-radius: var(--radius-md);
        transition: background-color 120ms ease, color 120ms ease;
        cursor: pointer;
    }


    .sidebar-item:hover {
        border-radius: var(--radius-md);
        background: var(--color-white);
    }


    /* ACTIVE STATE */
    .sidebar-item.active {
        background: color-mix(in oklab, var(--color-neutral-300) 40%, transparent);
        color: var(--color-neutral-900);
    }

    /* left accent bar */
    .sidebar-item.active::before {
        content: "";
        position: absolute;
        left: 0.25rem;
        top: 50%;
        transform: translateY(-50%);
        width: 3px;
        height: 70%;
        border-radius: 999px;
        background: var(--color-blue-600);      /* pick your brand color */
    }

    /* keep title truncation intact */
    .sidebar-item.active .sidebar-item__title {
        font-weight: 600;                        /* slight emphasis */
    }

    .sidebar-item__title,
    .sidebar-item span {
        white-space: nowrap;            /* prevent multi-line */
        overflow: hidden;               /* hide overflow */
        text-overflow: ellipsis;        /* add "..." */
        display: inline-block;
        max-width: 200px;               /* adjust to taste */
    }

    .sidebar-rename {
        font: inherit;
        color: inherit;
        background: var(--color-white);
        border: 1px solid var(--color-neutral-300);
        border-radius: .375rem;
        padding: 0 .5rem;

        line-height: 1.25rem;
        height: 1.75rem;         /* match row height */
        width: 100%;
        min-width: 0;            /* allow shrinking inside flex */

        outline: none;
    }
    .sidebar-rename:focus {
        border-color: var(--color-black);
        box-shadow: 0 0 0 3px color-mix(in oklab, var(--color-neutral-300) 20%, transparent);
    }

    .new-chat-btn {
        display: inline-flex;
        align-items: center;
        gap: .5rem;
        padding: .5rem .75rem;
        border-radius: .5rem;
        font-weight: 500;
        border: none;
        cursor: pointer;
        transition: background-color 150ms ease;
    }
    .new-chat-btn:hover {
        background: var(--color-white);
    }

    .delete-btn {
        opacity: 0;
        pointer-events: none; /* prevents accidental clicks when invisible */
        transition: opacity 120ms ease;
    }

    .sidebar-item:hover .delete-btn,
    .sidebar-item:focus-within .delete-btn {
        opacity: 1;
        pointer-events: auto;
    }


/* SVG pop effect — correctly scoped */
    :global(.delete-btn svg) {
        stroke-width: 1.8;
        transition: stroke-width 120ms ease, transform 120ms ease;
    }
    :global(.delete-btn:hover svg) {
        stroke-width: 2.6;
        transform: scale(1.4);
    }

    .sidebar-footer {
        margin-top: auto;                 
        padding-top: 1rem;
        padding-bottom: .5rem;
        text-align: center;
        color: var(--color-neutral-500);
        font-size: var(--text-xs);
        user-select: none;
    }

    .sidebar-closed .sidebar-header {
        flex-direction: column;       
        justify-content: flex-start;  
        align-items: center;          
        gap: .5rem;
        margin-bottom: 0;
    }

    .sidebar-closed .new-chat-btn {
        width: 36px;
        height: 36px;
        padding: 0;
        border-radius: var(--radius-lg);
        display: inline-flex; 
        align-items: center;
        justify-content: center;
    }

    .sidebar-closed .sidebar-toggle { order: 1; }   
    .sidebar-closed .new-chat-btn  { order: 2; }

    :global(.sidebar-toggle svg) { transition: transform 200ms ease; }
    :global(.sidebar-closed .sidebar-toggle svg) { transform: rotate(180deg); }
    
    .sidebar-toggle:hover,
    .sidebar-closed .new-chat-btn:hover {
        stroke-width: 2.6;
        transform: scale(1.4);
        background-color: var(--color-white);
    }


    .sidebar-closed .agent-list,
    .sidebar-closed .sidebar-list,
    .sidebar-closed .delete-btn,
    .sidebar-closed .sidebar-footer {
        display: none;
    }
    .sidebar-closed .new-chat-btn > span {
        display: none;
    }


</style>