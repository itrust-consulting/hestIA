import fs from 'node:fs/promises';
import path from 'node:path';
import { randomUUID } from 'node:crypto';
import { HELP_DIR, IMG_DIR } from './paths';
import { HelpError } from './errors';

export const SAFE_EXT = new Set(['.png', '.jpg', '.jpeg', '.gif', '.webp']);
export const MAX_BYTES = 10 * 1024 * 1024; // 10 MB

export function safeFilename(name: string): string {
  if (name.includes('/') || name.includes('\\') || name.includes('..')) {
    throw new HelpError(400, 'Invalid filename');
  }
  return name;
}

async function exists(p: string): Promise<boolean> {
  try {
    await fs.access(p);
    return true;
  } catch {
    return false;
  }
}

export interface ImageSummary {
  filename: string;
  url: string;
  size: number;
}

export async function listImages(): Promise<ImageSummary[]> {
  let entries: string[];
  try {
    entries = await fs.readdir(IMG_DIR);
  } catch {
    return [];
  }

  const withStats = await Promise.all(
    entries
      .filter((name) => SAFE_EXT.has(path.extname(name).toLowerCase()))
      .map(async (name) => {
        const stat = await fs.stat(path.join(IMG_DIR, name));
        return { filename: name, url: `/api/help/images/${name}`, size: stat.size, mtimeMs: stat.mtimeMs };
      })
  );
  withStats.sort((a, b) => b.mtimeMs - a.mtimeMs);
  return withStats.map(({ filename, url, size }) => ({ filename, url, size }));
}

export async function saveImage(data: Buffer, ext: string): Promise<{ filename: string; url: string }> {
  await fs.mkdir(IMG_DIR, { recursive: true });
  const filename = `${randomUUID().replace(/-/g, '')}${ext}`;
  await fs.writeFile(path.join(IMG_DIR, filename), data);
  return { filename, url: `/api/help/images/${filename}` };
}

export function imagePath(filename: string): string {
  safeFilename(filename);
  return path.join(IMG_DIR, filename);
}

export async function renameImage(oldName: string, newName: string): Promise<string> {
  safeFilename(oldName);
  safeFilename(newName);

  const src = path.join(IMG_DIR, oldName);
  if (!(await exists(src))) {
    throw new HelpError(404, 'Image not found');
  }
  if (!SAFE_EXT.has(path.extname(newName).toLowerCase())) {
    throw new HelpError(400, 'Invalid extension');
  }
  const dst = path.join(IMG_DIR, newName);
  if (await exists(dst)) {
    throw new HelpError(409, 'A file with that name already exists');
  }
  await fs.rename(src, dst);

  const oldUrl = `/api/help/images/${oldName}`;
  const newUrl = `/api/help/images/${newName}`;
  let mdFiles: string[] = [];
  try {
    mdFiles = (await fs.readdir(HELP_DIR)).filter((n) => n.endsWith('.md'));
  } catch {
    mdFiles = [];
  }
  for (const name of mdFiles) {
    const p = path.join(HELP_DIR, name);
    try {
      const text = await fs.readFile(p, 'utf-8');
      if (text.includes(oldUrl)) {
        await fs.writeFile(p, text.split(oldUrl).join(newUrl), 'utf-8');
      }
    } catch {
      // best-effort, matches backend's original swallow-and-continue behavior
    }
  }
  return newUrl;
}

export async function deleteImage(filename: string): Promise<void> {
  const p = imagePath(filename);
  if (!(await exists(p))) {
    throw new HelpError(404, 'Image not found');
  }
  await fs.unlink(p);
}
