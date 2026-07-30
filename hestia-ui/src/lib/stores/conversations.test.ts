import { describe, expect, it } from 'vitest';
import { get } from 'svelte/store';

import { hasMoreBefore, isLoadingOlder } from '$lib/stores/conversations';

// Smoke test: proves Vitest, the SvelteKit vite plugin, and $lib aliasing
// all resolve correctly together — not a behavioral test of pagination itself.
describe('conversations store (smoke test)', () => {
	it('resolves the $lib alias and loads the module', () => {
		expect(hasMoreBefore).toBeDefined();
	});

	it('has the documented initial values', () => {
		expect(get(hasMoreBefore)).toBe(false);
		expect(get(isLoadingOlder)).toBe(false);
	});
});
