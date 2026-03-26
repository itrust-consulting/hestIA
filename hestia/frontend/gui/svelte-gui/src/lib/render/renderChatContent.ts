import { marked } from './markdown';
import { renderKatex } from './katex';

export function renderChatContent(md: string): string {
  const html = marked.parse(md) as string;
  return renderKatex(html);
}