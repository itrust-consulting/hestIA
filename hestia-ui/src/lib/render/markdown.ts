import { marked, type Renderer } from 'marked';
import hljs from 'highlight.js';

marked.setOptions({ async: false });

// ── GitHub-style alert blocks ─────────────────────────────────────────────────
// Syntax:  > [!WARNING]
//          > Body text here.
//
// Supported types: NOTE, TIP, IMPORTANT, WARNING, CAUTION
// ─────────────────────────────────────────────────────────────────────────────
const ALERT_TYPES = ['NOTE', 'TIP', 'IMPORTANT', 'WARNING', 'CAUTION'] as const;
type AlertType = (typeof ALERT_TYPES)[number];

const ALERT_LABELS: Record<AlertType, string> = {
  NOTE:      'Note',
  TIP:       'Tip',
  IMPORTANT: 'Important',
  WARNING:   'Warning',
  CAUTION:   'Caution',
};

const ALERT_RE = new RegExp(
  `^> \\[!(${ALERT_TYPES.join('|')})\\]\\n((?:> ?[^\\n]*(?:\\n|$))*)`,
);

marked.use({
  extensions: [
    {
      name: 'alert',
      level: 'block',
      start(src: string) {
        return src.indexOf('> [!');
      },
      tokenizer(src: string) {
        const match = ALERT_RE.exec(src);
        if (!match) return;
        const alertType = match[1] as AlertType;
        const body = match[2].replace(/^> ?/gm, '').trim();
        const token: any = { type: 'alert', raw: match[0], alertType, text: body, tokens: [] };
        (this as any).lexer.blockTokens(body, token.tokens);
        return token;
      },
      renderer(token: any) {
        const label = ALERT_LABELS[token.alertType as AlertType] ?? token.alertType;
        const inner = (this as any).parser.parse(token.tokens);
        return `<div class="callout callout-${token.alertType.toLowerCase()}"><strong class="callout-label">${label}</strong>${inner}</div>\n`;
      },
    },
  ],
});

// ── Strip YAML frontmatter before rendering ───────────────────────────────────
marked.use({
  hooks: {
    preprocess(src: string): string {
      return src.replace(/^---\r?\n[\s\S]*?\r?\n---\r?\n/, '');
    },
  },
});

// ── Code blocks: mermaid passthrough, hljs for everything else ────────────────
const renderer: Partial<Renderer> = {
  html({ text }) {
    return text;
  },
  code(codeBlock) {
    const { text, lang } = codeBlock;

    if (lang === 'mermaid') {
      return `<pre class="mermaid">${text}</pre>`;
    }

    let highlighted: string;
    if (lang && hljs.getLanguage(lang)) {
      highlighted = hljs.highlight(text, { language: lang }).value;
    } else {
      highlighted = hljs.highlightAuto(text).value;
    }

    return `
    <div class="code-wrapper relative group">
        <button
        class="copy-btn absolute top-2 right-2 opacity-0 group-hover:opacity-100
                transition-opacity bg-neutral-700 text-white text-xs px-2 py-1 rounded"
        data-code="${encodeURIComponent(text)}"
        >
        Copy
        </button>

        <pre><code class="hljs language-${lang ?? ''}">${highlighted}</code></pre>
    </div>
    `;
  },
};

marked.use({ renderer });

export { marked };
