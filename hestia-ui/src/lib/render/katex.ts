// src/lib/katex.ts
import katex from 'katex';

const SIMPLE_MATH_REGEX =
/(?:(?<d>\${1,2})(?<bDollar>[\s\S]*?)\k<d>)|\((?<bParent>[^()]*?)\)|\[(?<bBracket>[^\[\]]*?)\]/g;


function sanitizeMathBody(expr: string): string {
  // 1) Decode the most common HTML entities that sneak into math
  //    (&amp;, &lt;, &gt;, quotes, apostrophes)
  const entityMap: Record<string, string> = {
    '&amp;': '&',
    '&lt;': '<',
    '&gt;': '>',
    '&quot;': '"',
    '&#39;': "'",
    '&#x27;': "'",          // the one you saw
    '&apos;': "'"
  };
  expr = expr.replace(/&(amp|lt|gt|quot|#39|#x27|apos);/g, m => entityMap[m] ?? m);

  // 2) Remove zero‑width / bidi control characters that break parsers
  //    ZWSP, ZWNJ, ZWJ, LRM, RLM, and friends
  expr = expr.replace(/[\u200B-\u200F\u202A-\u202E\u2060\uFEFF]/g, '');

  // 3) Replace common Unicode math symbols with LaTeX commands
  //    (helps when the model outputs θ, σ, Ω, “×”, superscripts, etc.)
  expr = expr
    .replace(/θ/g, '\\theta')
    .replace(/σ/g, '\\sigma')
    .replace(/Ω/g, '\\Omega')
    .replace(/π/g, '\\pi')
    .replace(/×/g, '\\times')
    // superscript ², ³ are common
    .replace(/²/g, '^{2}')
    .replace(/³/g, '^{3}');

  // 4) Normalize function names like "cos" (sometimes missing backslash or with strange combining marks)
  //    The character "⁡" (U+2061) appears after function names in some sources; strip it.
  expr = expr.replace(/\u2061/g, ''); // FUNCTION APPLICATION

  // If the model produced "cos" without backslash in a math context, we can add it conservatively:
  // Only add a backslash when "cos" is a standalone token
  expr = expr.replace(/(^|[^\\a-zA-Z])cos\b/g, '$1\\cos');
  expr = expr.replace(/(^|[^\\a-zA-Z])sin\b/g, '$1\\sin');
  expr = expr.replace(/(^|[^\\a-zA-Z])tan\b/g, '$1\\tan');

  // 5) Ensure there is a space around binary operators if missing (prevents token glue)
  expr = expr.replace(/([0-9a-zA-Z}_])([+\-*/=])([0-9a-zA-Z{\\])/g, '$1 $2 $3');

  // 6) Trim extra whitespace
  return expr.trim();
}


export function renderKatex(html: string): string {
  // Display math first
  html = html.replace(/\[[\s]{1}([^$]+?)[\s]{1}\]/g, (_, raw) => {
    const expr = sanitizeMathBody(raw);
    try {
      return katex.renderToString(expr, { displayMode: true, throwOnError: false });
    } catch {
      // On error, show the original $$...$$ so users still see something
      return `$$${raw}$$`;
    }
  });

    html = html.replace(/\([\s]{1}([^$]+?)[\s]{1}\)/g, (_, raw) => {
    const expr = sanitizeMathBody(raw);
    try {
      return katex.renderToString(expr, { displayMode: false, throwOnError: false });
    } catch {
      // On error, show the original $$...$$ so users still see something
      return `$${raw}$`;
    }
  });



  return html;
}
