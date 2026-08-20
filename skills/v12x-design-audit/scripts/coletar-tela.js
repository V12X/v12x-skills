/*
 * v12x-design-audit · coletor de TELA
 * ---------------------------------------------------------------------------
 * Varre o que está REALMENTE pintado na tela atual e tabula cada valor visual
 * com onde ele aparece. É a fonte de verdade: pega o que o código esconde
 * (estilo herdado, CSS de biblioteca, tema aplicado em runtime).
 *
 * Somente leitura — não altera nada na página.
 *
 * Como rodar:
 *   a) console do navegador: cole tudo e execute; o JSON é copiado/impresso;
 *   b) via ferramenta de browser do agente: executa e devolve o objeto;
 *   c) uma tela por vez — o nome da tela vira a etiqueta em "onde".
 *
 * Saída: { origem, tela, url, valores: { prop: { valor: {count, onde[]} } } }
 * que é o formato de entrada do mapear.py.
 */
(function coletarTela(nomeDaTela) {
  const TELA = nomeDaTela || document.title || location.pathname;

  // Propriedades que definem a identidade visual. Manter enxuto: cada uma vira
  // uma linha do relatório, e ruído aqui é ruído no veredito.
  const PROPS = [
    'color', 'background-color',
    'font-family', 'font-size', 'font-weight', 'line-height', 'letter-spacing',
    'border-top-left-radius', 'border-top-right-radius',
    'border-bottom-left-radius', 'border-bottom-right-radius',
    'border-top-width', 'border-top-color',
    'padding-top', 'padding-left', 'gap',
    'box-shadow',
  ];

  // Valores que não dizem nada sobre conformidade — descartar antes de contar.
  const VAZIO = new Set(['none', 'normal', 'auto', 'rgba(0, 0, 0, 0)', 'transparent',
                         '0px', '0', 'initial', 'inherit', 'unset']);

  const valores = {};
  let elementos = 0, invisiveis = 0;

  const seletor = (el) => {
    if (el.id) return '#' + el.id;
    const cls = (el.getAttribute && el.getAttribute('class') || '').trim().split(/\s+/)
      .filter(c => c && !/^(ng-|css-|sc-|jsx-)/.test(c)).slice(0, 2).join('.');
    const tag = el.tagName.toLowerCase();
    return cls ? `${tag}.${cls}` : tag;
  };

  document.querySelectorAll('*').forEach((el) => {
    const tag = el.tagName;
    if (tag === 'SCRIPT' || tag === 'STYLE' || tag === 'META' || tag === 'LINK') return;

    const cs = getComputedStyle(el);
    // Elemento invisível não define a identidade visual — mas CONTA como lacuna:
    // é conteúdo que a varredura desta tela não avaliou (estados, modais fechados).
    if (cs.display === 'none' || cs.visibility === 'hidden' || cs.opacity === '0') {
      invisiveis++; return;
    }
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) { invisiveis++; return; }
    elementos++;

    const onde = `${TELA} ${seletor(el)}`;
    for (const prop of PROPS) {
      let v = cs.getPropertyValue(prop);
      if (!v) continue;
      v = v.trim();
      if (!v || VAZIO.has(v)) continue;

      // Só conta a cor de texto se houver texto próprio visível — senão herda
      // e infla a contagem com elementos que não mostram nada.
      if (prop === 'color') {
        const texto = Array.from(el.childNodes)
          .some(n => n.nodeType === 3 && n.textContent.trim().length > 0);
        if (!texto) continue;
      }
      // Idem para fundo: só conta se realmente pinta.
      if (prop === 'background-color' && /rgba\(.*,\s*0\)$/.test(v)) continue;

      valores[prop] = valores[prop] || {};
      const slot = valores[prop][v] = valores[prop][v] || { count: 0, onde: [] };
      slot.count++;
      if (slot.onde.length < 5 && !slot.onde.includes(onde)) slot.onde.push(onde);
    }
  });

  const saida = {
    origem: 'tela',
    tela: TELA,
    url: location.href,
    viewport: `${innerWidth}x${innerHeight}`,
    tema: matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light',
    elementos_visiveis: elementos,
    nao_avaliados: invisiveis,   // entra no mapa de cobertura
    valores,
  };

  // Conveniência no console: copia e resume.
  try { if (typeof copy === 'function') copy(JSON.stringify(saida, null, 2)); } catch (e) {}
  console.log(`[v12x] tela "${TELA}" · ${elementos} elementos visíveis · `
    + `${invisiveis} não avaliados (ocultos/zero-size) · tema ${saida.tema}`);
  console.log('[v12x] NÃO COBERTO nesta varredura: estados (hover/foco/erro/disabled), '
    + 'modais fechados, outro tema, outro viewport. Varra cada um separadamente.');
  return saida;
})();
