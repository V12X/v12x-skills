// v12x-flow · instrumentar.js — auditoria determinística de UM estado da tela
// -----------------------------------------------------------------------------
// Roda no navegador. Instala captadores de erro de runtime (para as próximas
// ações), audita os controles do estado ATUAL e devolve os FATOS. O agente dirige
// (clica, digita, completa o fluxo) e re-roda isto + lê console e rede via as
// ferramentas do navegador após cada ação. É a Fase 0: operar, não opinar.
//
//   window.__V12X_STATE__ = 'login-vazio'   // nomeie o estado antes de rodar
//
// A camada de julgamento (heurística) NÃO sai daqui — só o medível.
(() => {
  window.__V12X_ERR__ = window.__V12X_ERR__ || [];
  if (!window.__v12x_hooked) {
    window.__v12x_hooked = true;
    window.addEventListener('error', e => window.__V12X_ERR__.push('error: ' + (e.message || e.type)));
    window.addEventListener('unhandledrejection', e =>
      window.__V12X_ERR__.push('promise rejeitada: ' + ((e.reason && e.reason.message) || e.reason)));
  }
  const vis = el => {
    const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    return r.width > 0 && r.height > 0 && cs.visibility !== 'hidden' && cs.display !== 'none' && +cs.opacity !== 0;
  };
  const F = {
    estado: window.__V12X_STATE__ || '(sem nome)',
    tapAlvo: [], semLabel: [], semNomeAcessivel: [], formSemValidacao: [], cliqueMorto: [],
    errosDeRuntime: window.__V12X_ERR__.slice(-12)
  };
  // controles interativos
  document.querySelectorAll('button, a[href], input, textarea, select, [role="button"]').forEach(el => {
    if (!vis(el)) return;
    const r = el.getBoundingClientRect(), tag = el.tagName.toLowerCase();
    const nome = (el.textContent || el.getAttribute('aria-label') || el.value || '').trim();
    // alvo de toque < 44px (mínimo de acessibilidade/mobile), exceto links inline
    if ((r.height < 44 || r.width < 44) && tag !== 'a')
      F.tapAlvo.push(`${tag} “${nome.slice(0, 20)}” ${Math.round(r.width)}x${Math.round(r.height)}px`);
    // botão sem nome acessível (e sem ícone que o justifique)
    if ((tag === 'button' || el.getAttribute('role') === 'button') && !nome && !el.querySelector('svg, img'))
      F.semNomeAcessivel.push(`${tag} sem rótulo nem aria-label`);
  });
  // campos sem label programático (placeholder não é label: some ao digitar)
  document.querySelectorAll('input, textarea, select').forEach(el => {
    if (!vis(el)) return;
    const lab = (el.id && document.querySelector(`label[for="${CSS.escape(el.id)}"]`)) ||
      el.getAttribute('aria-label') || el.getAttribute('aria-labelledby') || el.closest('label');
    if (!lab) F.semLabel.push(`input[${el.placeholder || el.type}]${el.placeholder ? ' (só placeholder)' : ''}`);
  });
  // formulário que não valida (submit vazio não dá feedback)
  document.querySelectorAll('form').forEach(f => {
    const campos = [...f.querySelectorAll('input, textarea, select')];
    if (campos.length && !campos.some(i => i.hasAttribute('required')))
      F.formSemValidacao.push(`form com ${campos.length} campo(s), nenhum required — submit vazio não valida`);
  });
  // parece clicável, sem handler (dead control)
  document.querySelectorAll('[class*="btn"], [class*="button"], [class*="clickable"]').forEach(el => {
    if (!vis(el)) return;
    const tag = el.tagName.toLowerCase();
    if (tag === 'button' || tag === 'a' || el.onclick || el.getAttribute('role') === 'button') return;
    F.cliqueMorto.push(`${tag}.${String(el.className).slice(0, 24)} parece clicável, sem handler`);
  });
  return JSON.stringify(F, null, 0);
})()
