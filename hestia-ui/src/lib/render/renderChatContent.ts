import DOMPurify from 'isomorphic-dompurify';
import { marked } from './markdown';
import { renderKatex } from './katex';
import type { Citation } from '$lib/types';

export function stripThinkingPreamble(text: string): string {
  return text.replace(/^[\s\S]*?thinking\s+process[:\s]*\n+/i, '');
}

export function renderChatContent(md: string): string {
  const html = marked.parse(md) as string;
  const withMath = renderKatex(html);
  return DOMPurify.sanitize(withMath);
}

function escAttr(s: string): string {
  return s.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function shortLabel(c: Citation): string {
  const base = c.subject || c.source.split('/').pop()?.replace(/\.[^.]+$/, '') || c.source;
  return base.length > 18 ? base.substring(0, 17) + '…' : base;
}

// Strip the LLM-generated "Source:" block the model sometimes appends.
// Only applied when we have citation chip data so the block is truly redundant.
function stripSourcesBlock(md: string): string {
  return md.replace(/\n{1,2}\**Sources?:?\**\s*\n[\s\S]*$/i, '').trimEnd();
}

function normalizeKey(k: string): string {
  return k.replace(/[^a-zA-Z0-9]/g, '').toLowerCase();
}

export function renderWithCitations(md: string, citations?: Citation[]): string {
  const cleaned = citations?.length ? stripSourcesBlock(md) : md;
  const html = renderChatContent(cleaned);
  if (!citations?.length) return html;

  // Each retrieved chunk gets its own unique key (see _format_citations in
  // handler.py), so a key normally maps to exactly one citation. Still grouped
  // into arrays because a single \cite{} marker can reference several keys
  // together (\cite{1,2}) when a claim draws on more than one chunk -- that
  // case must page through all of them, not just the first.
  const citationMap = new Map<string, Citation[]>();
  for (const c of citations) {
    const k = normalizeKey(c.key);
    const group = citationMap.get(k);
    if (group) group.push(c);
    else citationMap.set(k, [c]);
  }

  return html.replace(/\\cite\{([^}]+)\}/g, (_match, group: string) => {
    const keys = group.split(',').map((s: string) => s.trim());
    const first = citationMap.get(normalizeKey(keys[0]))?.[0];
    if (!first) return _match;

    const label = shortLabel(first);
    const chipCitations = keys.flatMap(k => citationMap.get(normalizeKey(k)) ?? []);
    const extra = chipCitations.length > 1 ? ` +${chipCitations.length - 1}` : '';

    return `<span class="cite-chip" data-cites="${escAttr(JSON.stringify(chipCitations))}">${escAttr(label)}${extra}</span>`;
  });
}
