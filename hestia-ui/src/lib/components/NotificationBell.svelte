<script lang="ts">
  import BellIcon from '$lib/components/icons/bellIcon.svelte';
  import Modal from '$lib/components/Modal.svelte';
  import { tooltip } from '$lib/actions/tooltip';
  import { goto } from '$app/navigation';
  import { unreadCount, notifications, notificationsLoading, fetchNotifications, markRead, markAllRead } from '$lib/stores/notifications';
  import { renderChatContent } from '$lib/render/renderChatContent';
  import { sendHeartbeat } from '$lib/auth/session';
  import type { Notification } from '$lib/types';

  let open = $state(false);
  let containerEl: HTMLDivElement | undefined = $state();
  let viewingNotification: Notification | null = $state(null);

  // Manual subscription into a rune instead of the legacy `$unreadCount`
  // auto-subscription syntax -- unreadCount is written from session.ts's
  // setInterval/heartbeat, entirely outside this component's own effects,
  // and this sidesteps that store/runes interop path in case it's the
  // source of the badge not refreshing without a full reload.
  let unreadCountValue = $state(0);
  $effect(() => {
    return unreadCount.subscribe((v) => {
      unreadCountValue = v;
    });
  });

  function relativeTime(ts: number): string {
    const diffMs = Date.now() - ts;
    const mins = Math.floor(diffMs / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hrs = Math.floor(mins / 60);
    if (hrs < 24) return `${hrs}h ago`;
    const days = Math.floor(hrs / 24);
    return `${days}d ago`;
  }

  function toggle() {
    open = !open;
    if (open) {
      // Refresh the unread count immediately rather than waiting for the
      // next 45s heartbeat tick -- otherwise a badge that just changed
      // (e.g. a new notification arrived) only updates on reload.
      fetchNotifications();
      sendHeartbeat();
    }
  }

  async function handleClick(n: Notification) {
    await markRead(n.id);
    open = false;
    if (n.type === 'system') {
      viewingNotification = n;
    } else if (n.link) {
      goto(n.link);
    }
  }

  function openNotificationLink() {
    const link = viewingNotification?.link;
    viewingNotification = null;
    if (link) goto(link);
  }

  function handleOutsideClick(event: MouseEvent) {
    if (open && containerEl && !containerEl.contains(event.target as Node)) {
      open = false;
    }
  }

  $effect(() => {
    if (!open) return;
    window.addEventListener('click', handleOutsideClick, true);
    return () => window.removeEventListener('click', handleOutsideClick, true);
  });
</script>

<div class="relative" bind:this={containerEl}>
  <button class="icon-btn notif-trigger" onclick={toggle} aria-label="Notifications" use:tooltip={"Notifications"}>
    <BellIcon />
    {#if unreadCountValue > 0}
      <span class="notif-badge">{unreadCountValue > 99 ? '99+' : unreadCountValue}</span>
    {/if}
  </button>

  {#if open}
    <div class="notification-dropdown">
      <div class="notif-header">
        <span>Notifications</span>
        {#if $notifications.some(n => !n.is_read)}
          <button class="notif-mark-all" onclick={() => markAllRead()}>Mark all read</button>
        {/if}
      </div>
      <div class="notif-list">
        {#if $notificationsLoading}
          <p class="notif-empty">Loading…</p>
        {:else if $notifications.length === 0}
          <p class="notif-empty">You're all caught up.</p>
        {:else}
          {#each $notifications as n (n.id)}
            <!-- svelte-ignore a11y_click_events_have_key_events -->
            <!-- svelte-ignore a11y_no_static_element_interactions -->
            <div class="notif-item" class:unread={!n.is_read} onclick={() => handleClick(n)}>
              {#if !n.is_read}<span class="notif-dot"></span>{/if}
              <div class="notif-item-body">
                <p class="notif-title">{n.title}</p>
                {#if n.body}<p class="notif-body">{n.body}</p>{/if}
                <p class="notif-time">{relativeTime(n.created_at)}</p>
              </div>
            </div>
          {/each}
        {/if}
      </div>
    </div>
  {/if}
</div>

<Modal title={viewingNotification?.title ?? 'Notification'} open={viewingNotification !== null} onClose={() => (viewingNotification = null)}>
  <div class="notif-modal-body prose prose-sm max-w-none">
    {#if viewingNotification?.body}
      {@html renderChatContent(viewingNotification.body)}
    {/if}
  </div>
  <svelte:fragment slot="footer">
    {#if viewingNotification?.link}
      <button class="btn-primary" onclick={openNotificationLink}>Open link</button>
    {/if}
  </svelte:fragment>
</Modal>

<style>
  .notif-trigger {
    position: relative;
  }

  .notif-badge {
    position: absolute;
    top: 0;
    right: 0;
    min-width: 1rem;
    height: 1rem;
    padding: 0 .25rem;
    border-radius: 999px;
    background: var(--color-red-300, #dc2626);
    color: white;
    font-size: .6rem;
    line-height: 1rem;
    font-weight: 600;
    text-align: center;
  }

  .notification-dropdown {
    position: absolute;
    right: 0;
    margin-top: calc(var(--spacing) * 4);
    width: 22rem;
    max-height: 26rem;
    z-index: 1000;
    display: flex;
    flex-direction: column;

    border: 1px solid var(--color-neutral-200);
    border-radius: var(--radius-xl);
    box-shadow: 0 12px 24px color-mix(in oklab, black 18%, transparent);
    background-color: var(--color-white);
    overflow: hidden;
  }

  .notif-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: .6rem .9rem;
    border-bottom: 1px solid var(--color-neutral-200);
    font-weight: 600;
    font-size: var(--text-sm);
    flex-shrink: 0;
  }

  .notif-mark-all {
    font-weight: 500;
    font-size: .75rem;
    color: var(--color-blue-600, #2563eb);
    background: transparent;
    border: none;
    cursor: pointer;
  }
  .notif-mark-all:hover {
    text-decoration: underline;
  }

  .notif-list {
    overflow-y: auto;
  }

  .notif-empty {
    padding: 1.5rem .9rem;
    text-align: center;
    color: var(--color-neutral-400);
    font-size: var(--text-sm);
  }

  .notif-item {
    display: flex;
    gap: .5rem;
    padding: .65rem .9rem;
    cursor: pointer;
    border-bottom: 1px solid var(--color-neutral-100);
    transition: background-color 120ms ease;
  }
  .notif-item:last-child {
    border-bottom: none;
  }
  .notif-item:hover {
    background: var(--color-neutral-50);
  }
  .notif-item.unread .notif-title {
    font-weight: 700;
  }

  .notif-dot {
    flex-shrink: 0;
    width: .45rem;
    height: .45rem;
    margin-top: .4rem;
    border-radius: 999px;
    background: var(--color-blue-600, #2563eb);
  }

  .notif-item-body {
    min-width: 0;
    flex: 1 1 auto;
  }

  .notif-title {
    margin: 0;
    font-size: var(--text-sm);
    color: var(--color-neutral-900);
  }

  .notif-body {
    margin: .15rem 0 0;
    font-size: .75rem;
    color: var(--color-neutral-500);
    overflow: hidden;
    text-overflow: ellipsis;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    line-clamp: 2;
    -webkit-box-orient: vertical;
  }

  .notif-time {
    margin: .25rem 0 0;
    font-size: .7rem;
    color: var(--color-neutral-400);
  }

  .notif-modal-body {
    font-size: var(--text-sm);
    color: var(--color-neutral-700);
  }

  .btn-primary {
    background: var(--color-blue-600); color: white;
    padding: 0.5rem 1.25rem; border-radius: var(--radius-lg);
    font-weight: 600; font-size: var(--text-sm); border: none; cursor: pointer;
  }
  .btn-primary:hover { background: var(--color-blue-700); }
</style>
