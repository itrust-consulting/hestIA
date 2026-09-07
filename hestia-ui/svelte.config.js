import adapter from '@sveltejs/adapter-node';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		adapter: adapter(),
		// Explicit rather than relying on the (identical) framework default --
		// this is the only CSRF defense on state-changing BFF routes (no
		// separate anti-CSRF token scheme layered on top), so it should be a
		// visible, deliberate setting rather than an implicit one.
		// trustedOrigins (not the deprecated checkOrigin) is SvelteKit's
		// current API for this; an empty list keeps origin-checking on with
		// no cross-origin exceptions.
		csrf: {
			trustedOrigins: []
		},
		csp: {
			mode: 'nonce',
			directives: {
				'default-src': ['self'],
				'script-src': ['self'],
				'style-src': ['self', 'unsafe-inline'],
				'img-src': ['self', 'data:', 'blob:'],
				'font-src': ['self'],
				'connect-src': ['self'],
				'frame-ancestors': ['none'],
				'base-uri': ['self'],
			},
		},
		version: {
			name: 'v0.2.3'
		}
	},
};

export default config;