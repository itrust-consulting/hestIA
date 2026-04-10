<script lang="ts">
  export let user: {
    id: string;
    username: string;
    email: string;
    first_name: string;
    last_name: string;
    created_at: number;
    updated_at: number;
    expires_at: number;
    orgs: Record<string, any>;
    roles: Record<string, any>;
  };

  const orgs: string[] = user.orgs.map((o: { name: any; }) => o.name);
  const roles: string[] = user.roles.map((r: { name: any; }) => r.name);

  const formatDate = (ts: number) => {
    if (!ts) return '';
    return new Date(ts).toLocaleString(undefined, {
      year: "numeric",
      month: "long",
      day: "numeric",
    });
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
      <p class="profile-email">{user.email}</p>
    </div>
  </div>

  <!-- GRID INFO -->
  <div class="profile-details-grid">
    <div class="detail">
      <label>Name</label>
      <p>{user.first_name} {user.last_name}</p>
    </div>

    <div class="detail">
      <label>Organization</label>
      <p>{orgs}</p>
    </div>

    <div class="detail">
      <label>Roles</label>
      <p>{roles}</p>
    </div>

    <div class="detail full">
      <label>Created</label>
      <p>{formatDate(user.created_at)}</p>
    </div>
    
    {#if user.expires_at}
      <div class="detail full">
        <label>Expires</label>
        <p>{formatDate(user.expires_at)}</p>
      </div>
    {/if}
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

  .profile-email {
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

</style>