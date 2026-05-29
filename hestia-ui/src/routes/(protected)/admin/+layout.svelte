<script lang="ts">
  import AdminSidebar from '$lib/components/AdminSidebar.svelte';
  const { children } = $props();
</script>

<div class="admin-shell">
  <AdminSidebar />
  <div class="admin-main">
    {@render children()}
  </div>
</div>

<style>
.admin-shell {
  display: flex;
  flex: 1;
  min-height: 0;
  overflow: hidden;
  background: var(--color-neutral-100);
}

.admin-main {
  flex: 1;
  overflow-y: auto;
}
</style>
