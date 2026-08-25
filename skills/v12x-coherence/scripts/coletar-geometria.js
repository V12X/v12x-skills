// v12x-coherence · coletar-geometria.js
// -----------------------------------------------------------------------------
// Roda no NAVEGADOR (console, ou pela ferramenta de browser do agente), uma tela
// por vez. Extrai a geometria real de cada elemento visível — a fonte de verdade
// do que está pintado. É o que permite achar desalinhamento de 2-3px, que o olho
// sente e não nomeia. Saída: JSON para o inferir.py.
//
//   SCREEN = 'login'  // nomeie a tela; vira etiqueta no relatório
//
// Cole isto no console (ajustando SCREEN) e salve a saída como geometria-<tela>.json.
(() => {
  const SCREEN = (window.__V12X_SCREEN__ || 'tela');
  const out = [], seen = new Set();
  document.querySelectorAll('body *').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width < 16 || r.height < 8) return;          // ruído: ícone minúsculo, spacer
    if (r.width >= innerWidth - 1) return;             // container full-bleed não alinha nada
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || +cs.opacity === 0) return;
    const tag = el.tagName.toLowerCase();
    let txt = (tag === 'input') ? ('input[' + (el.placeholder || el.type) + ']')
            : (el.children.length === 0 ? (el.textContent || '').trim().slice(0, 24) : '');
    const label = (tag + (txt ? ' “' + txt + '”' : '')).slice(0, 34);
    const key = [Math.round(r.left), Math.round(r.top), Math.round(r.width), Math.round(r.height)].join(',');
    if (seen.has(key)) return; seen.add(key);
    const isText = el.children.length === 0 && txt && tag !== 'input';
    out.push({
      screen: SCREEN, el: label,
      L: +r.left.toFixed(1), R: +r.right.toFixed(1),
      T: +r.top.toFixed(1), B: +r.bottom.toFixed(1),
      W: +r.width.toFixed(1), H: +r.height.toFixed(1),
      cx: +((r.left + r.right) / 2).toFixed(1),
      fs: isText ? Math.round(parseFloat(cs.fontSize) * 10) / 10 : null,
      fw: isText ? cs.fontWeight : null
    });
  });
  return JSON.stringify({ screen: SCREEN, vw: innerWidth, theme: document.documentElement.dataset.theme || 'default', items: out }, null, 0);
})()
