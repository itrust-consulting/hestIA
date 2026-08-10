import path from 'node:path';
import { env } from '$env/dynamic/private';

export const HELP_DIR = path.resolve(
  env.PRIVATE_HELP_DATA_DIR || path.join(process.cwd(), 'data', 'manual')
);
export const IMG_DIR = path.join(HELP_DIR, 'images');
