import { marked, type Renderer } from 'marked';
import hljs from 'highlight.js';

marked.setOptions( {async: false} )

const renderer: Partial<Renderer> = {
    code(codeBlock) {
        const { text, lang } = codeBlock;

        let highlighted: string;
        if (lang && hljs.getLanguage(lang)) {
        highlighted = hljs.highlight(text, { language: lang }).value;
        } else {
        highlighted = hljs.highlightAuto(text).value;
        }

        // Wrap the <pre><code> block so we can attach a button
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
    }
};
marked.use({ renderer });

export { marked };
  