<script lang="ts">
  export let user: {
    id: string;
    username: string;
    roles: string[];
    permissions: Record<string, any>;
  };
</script>

<h1 class="section-title">Profile</h1>

<div class="profile-card">
  <!-- HEADER -->
  <div class="profile-header">
    <div class="avatar">
      {user.username.charAt(0).toUpperCase()}
    </div>

    <div class="profile-basic">
      <h2 class="profile-name">{user.username}</h2>
      <p class="profile-role">{user.roles.join(', ')}</p>
    </div>
  </div>

  <!-- GRID INFO -->
  <div class="profile-details-grid">
    <div class="detail">
      <label>User ID</label>
      <p>{user.id}</p>
    </div>

    <div class="detail">
      <label>Username</label>
      <p>{user.username}</p>
    </div>

    <div class="detail">
      <label>Roles</label>
      <p>{user.roles.join(', ')}</p>
    </div>

    <div class="detail full">
      <label>Permissions</label>
      <pre class="permissions-box">{JSON.stringify(user.permissions, null, 2)}</pre>
    </div>
  </div>

</div>

<style>
  .section-title {
    font-size: var(--text-xl);
    font-weight: 700;
    margin-bottom: 1.5rem;
  }

  .profile-card {
    background: white;
    padding: 1.75rem;
    border-radius: var(--radius-2xl);
    box-shadow: 0 4px 20px rgba(0,0,0,0.06);
    display: flex;
    flex-direction: column;
    gap: 1.75rem;
  }

  .profile-header {
    display: flex;
    gap: 1rem;
    align-items: center;
  }

  .avatar {
    width: 60px;
    height: 60px;
    border-radius: 999px;
    background: color-mix(in srgb, var(--color-blue-600) 80%, transparent);
    color: white;
    font-size: var(--text-2xl);
    font-weight: 600;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .profile-name {
    font-size: var(--text-lg);
    font-weight: 600;
  }

  .profile-role {
    color: var(--color-neutral-600);
    font-size: var(--text-sm);
  }

  .profile-details-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 1.25rem 2rem;
  }

  .detail label {
    color: var(--color-neutral-600);
    font-size: var(--text-xs);
    text-transform: uppercase;
  }

  .detail p {
    margin-top: 4px;
    font-weight: 500;
  }

  .detail.full {
    grid-column: 1 / -1;
  }

  .permissions-box {
    background: var(--color-neutral-100);
    padding: 0.75rem;
    border-radius: var(--radius-lg);
    font-size: var(--text-xs);
    max-height: 160px;
    overflow-y: auto;
    border: 1px solid var(--color-neutral-300);
  }

  .profile-actions {
    display: flex;
    gap: 1rem;
  }

  .btn {
    padding: .65rem 1.25rem;
    border-radius: var(--radius-lg);
    font-weight: 600;
    cursor: pointer;
    border: none;
    transition: background 120ms ease;
  }

  .btn.dark {
    background: var(--color-blue-600);
    color: white;
  }
  .btn.dark:hover {
    background: var(--color-blue-700);
  }

  .btn.light {
    background: var(--color-neutral-200);
    color: var(--color-neutral-900);
  }
  .btn.light:hover {
    background: var(--color-neutral-300);
  }
</style>