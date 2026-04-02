import adapter from '@sveltejs/adapter-node';

const version = 'v0.2.1'

/** @type {import('@sveltejs/kit').Config} */
const config = {
	kit: {
		adapter: adapter()
	},
	env: {
		VERSION: version,
	}
};

export default config;