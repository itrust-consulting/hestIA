import fs from 'node:fs/promises';
import path from 'node:path';
import { HELP_DIR } from './paths';
import { parseFrontmatter, extractTitle } from './frontmatter';
import { HelpError } from './errors';

const SLUG_RE = /^[a-z0-9][a-z0-9-]*$/;

export function validateSlug(section: string): string {
  if (!SLUG_RE.test(section)) {
    throw new HelpError(400, 'Invalid section name — use lowercase letters, digits, and hyphens only');
  }
  return section;
}

function sectionPath(section: string): string {
  validateSlug(section);
  return path.join(HELP_DIR, `${section}.md`);
}

export interface SectionSummary {
  id: string;
  title: string;
}

export async function listSections(): Promise<SectionSummary[]> {
  let entries: string[];
  try {
    entries = await fs.readdir(HELP_DIR);
  } catch {
    return [];
  }

  const items: (SectionSummary & { order: number })[] = [];
  for (const name of entries) {
    if (!name.endsWith('.md')) continue;
    const slug = name.slice(0, -3);
    if (!SLUG_RE.test(slug)) continue;

    let raw = '';
    try {
      raw = await fs.readFile(path.join(HELP_DIR, name), 'utf-8');
    } catch {
      raw = '';
    }
    const { meta, body } = parseFrontmatter(raw);
    const title = meta.title || extractTitle(body, slug);
    const parsedOrder = Number.parseInt(meta.order ?? '', 10);
    const order = Number.isFinite(parsedOrder) ? parsedOrder : 999;
    items.push({ id: slug, title, order });
  }

  items.sort((a, b) => a.order - b.order || a.id.localeCompare(b.id));
  return items.map(({ id, title }) => ({ id, title }));
}

export async function getSection(section: string): Promise<string | null> {
  const p = sectionPath(section);
  try {
    return await fs.readFile(p, 'utf-8');
  } catch {
    return null;
  }
}

export async function putSection(section: string, content: string): Promise<void> {
  const p = sectionPath(section);
  await fs.mkdir(HELP_DIR, { recursive: true });
  await fs.writeFile(p, content, 'utf-8');
}

export async function deleteSection(section: string): Promise<boolean> {
  const p = sectionPath(section);
  try {
    await fs.unlink(p);
    return true;
  } catch {
    return false;
  }
}
