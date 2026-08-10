const FM_RE = /^---\r?\n([\s\S]*?)\r?\n---\r?\n/;

export type Frontmatter = Record<string, string>;

export function parseFrontmatter(content: string): { meta: Frontmatter; body: string } {
  const m = FM_RE.exec(content);
  if (!m) return { meta: {}, body: content };
  const meta: Frontmatter = {};
  for (const line of m[1].split(/\r?\n/)) {
    const idx = line.indexOf(':');
    if (idx === -1) continue;
    const key = line.slice(0, idx).trim();
    const val = line
      .slice(idx + 1)
      .trim()
      .replace(/^["']+|["']+$/g, '');
    meta[key] = val;
  }
  return { meta, body: content.slice(m[0].length) };
}

export function extractTitle(body: string, slug: string): string {
  for (const line of body.split(/\r?\n/)) {
    const stripped = line.trim();
    if (stripped.startsWith('# ')) return stripped.slice(2).trim();
  }
  return slug
    .split('-')
    .map((w) => (w ? w[0].toUpperCase() + w.slice(1).toLowerCase() : w))
    .join(' ');
}
