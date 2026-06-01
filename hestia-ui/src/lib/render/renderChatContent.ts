import { browser } from '$app/environment';
import DOMPurify from 'dompurify';
import { marked } from './markdown';
import { renderKatex } from './katex';
import type { Citation } from '$lib/types';

export function stripThinkingPreamble(text: string): string {
  return text.replace(/^[\s\S]*?thinking\s+process[:\s]*\n+/i, '');
}

export function renderChatContent(md: string): string {
  const html = marked.parse(md) as string;
  const withMath = renderKatex(html);
  return browser ? DOMPurify.sanitize(withMath) : withMath;
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

  const citationMap = new Map(citations.map(c => [normalizeKey(c.key), c]));

  return html.replace(/\\cite\{([^}]+)\}/g, (_match, group: string) => {
    const keys = group.split(',').map((s: string) => s.trim());
    const first = citationMap.get(normalizeKey(keys[0]));
    if (!first) return _match;

    const label = shortLabel(first);
    const extra = keys.length > 1 ? ` +${keys.length - 1}` : '';
    const chipCitations = keys
      .map(k => citationMap.get(normalizeKey(k)))
      .filter(Boolean);

    return `<span class="cite-chip" data-cites="${escAttr(JSON.stringify(chipCitations))}">${escAttr(label)}${extra}</span>`;
  });
}
