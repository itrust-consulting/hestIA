
<script lang="ts">
  import type { PageData } from './$types';
  import ProfileCard from '$lib/components/account/ProfileCard.svelte';

  export let data: PageData;

  const { user } = data;
</script>

<ProfileCard {user}></ProfileCard>