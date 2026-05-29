import DOMPurify from 'dompurify';

export function tooltip(node: HTMLElement, html: string) {
  let tip: HTMLDivElement | null = null;

  function show() {
    if (!html?.trim()) return;
    tip = document.createElement('div');
    tip.className = 'tooltip-portal';
    tip.innerHTML = DOMPurify.sanitize(html);
    tip.style.visibility = 'hidden';
    document.body.appendChild(tip);

    requestAnimationFrame(() => {
      if (!tip) return;
      const anchor = node.getBoundingClientRect();
      const tipRect = tip.getBoundingClientRect();

      let top = anchor.top - tipRect.height - 8;
      if (top < 8) top = anchor.bottom + 8;

      let left = anchor.left + anchor.width / 2 - tipRect.width / 2;
      left = Math.max(8, Math.min(left, window.innerWidth - tipRect.width - 8));

      tip.style.top  = `${top}px`;
      tip.style.left = `${left}px`;
      tip.style.visibility = '';
    });
  }

  function hide() {
    tip?.remove();
    tip = null;
  }

  node.addEventListener('mouseenter', show);
  node.addEventListener('mouseleave', hide);
  node.addEventListener('focus',      show);
  node.addEventListener('blur',       hide);

  return {
    update(newHtml: string) { html = newHtml; },
    destroy() {
      hide();
      node.removeEventListener('mouseenter', show);
      node.removeEventListener('mouseleave', hide);
      node.removeEventListener('focus',      show);
      node.removeEventListener('blur',       hide);
    },
  };
}
