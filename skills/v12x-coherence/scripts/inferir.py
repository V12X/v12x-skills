#!/usr/bin/env python3
"""
v12x-coherence · inferir.py — o motor
-----------------------------------------------------------------------------
Infere a régua que o app JÁ usa (sem design system dado) e aponta onde ele se
contradiz. Recebe a geometria coletada no navegador (uma ou mais telas) e:

  1. Alinhamento: por tela, acha a borda dominante (a linha que o app 'quer') e
     marca os elementos QUASE alinhados (1..8px) — defeito. Ignora os longe
     (>8px): alinhamento próprio é decisão, não engano.
  2. Ritmo vertical: os gaps entre elementos empilhados; o fora do ritmo dominante.
  3. Escala implícita: agrupa espaçamentos/larguras e marca os fora do agrupamento.

Não julga gosto nem hierarquia de significado — mede consistência.

  python3 inferir.py geometria-*.json [--emitir-tokens tokens.json]

Regra dura: este script SÓ mede e reporta. Ele não edita arquivo nenhum.
"""
import json, sys, glob
from collections import Counter

NEAR = 8.0   # px: dentro disto da borda dominante = quase-alinhado = DEFEITO
             #     além disto = alinhamento próprio = decisão, ignora

def carregar(paths):
    telas = []
    for pat in paths:
        for p in glob.glob(pat):
            d = json.load(open(p))
            telas.append(d)
    return telas

def cluster1d(vals, tol=1.5):
    """agrupa valores próximos; devolve [(centro, [membros])] do maior ao menor."""
    vs = sorted(vals)
    grupos = []
    for v in vs:
        if grupos and v - grupos[-1][-1] <= tol:
            grupos[-1].append(v)
        else:
            grupos.append([v])
    cent = [(round(sum(g)/len(g), 1), g) for g in grupos]
    return sorted(cent, key=lambda c: -len(c[1]))

def dominante(vals, tol=1.5):
    c = cluster1d(vals, tol)
    return (c[0][0], len(c[0][1])) if c else (None, 0)

def alinhamento(tela, achados):
    its = [i for i in tela['items'] if i['W'] < tela.get('vw', 99999) - 1]
    for eixo, key in (('borda esquerda', 'L'), ('borda direita', 'R')):
        vals = [i[key] for i in its]
        dom, n = dominante(vals)
        if dom is None or n < 3:      # sem uma linha forte, não há norma implícita
            continue
        for i in its:
            d = round(i[key] - dom, 1)
            if 0 < abs(d) <= NEAR:    # quase-alinhado = defeito
                sev = 'alta' if n >= 4 and abs(d) >= 2 else 'media'
                achados.append((sev, tela['screen'],
                    f"{i['el']}: {eixo} em {i[key]}px, {d:+.0f}px da linha do app ({dom}px, {n} elementos) — puxar {-d:+.0f}px"))

def ritmo(tela, achados):
    its = sorted([i for i in tela['items'] if i['W'] < tela.get('vw', 99999) - 1], key=lambda i: i['T'])
    gaps = []
    prev = None
    for i in its:
        if prev and i['T'] >= prev['B'] - 1:
            gaps.append((round(i['T'] - prev['B'], 1), prev['el'], i['el']))
        prev = i
    if len(gaps) < 3:
        return
    dom, n = dominante([g[0] for g in gaps])
    if dom is None or n < 3:
        return
    for g, a, b in gaps:
        d = round(g - dom, 1)
        if 0 < abs(d) <= NEAR:
            achados.append(('media', tela['screen'],
                f"ritmo: {a} → {b} com gap {g}px, {d:+.0f}px do ritmo do app ({dom}px)"))

def escala_larguras(telas, achados):
    """larguras repetidas definem a escala; a quase-igual é provável engano."""
    todas = [round(i['W']) for t in telas for i in t['items'] if i['W'] < t.get('vw', 99999) - 1]
    c = cluster1d(todas, tol=2)
    fortes = [ct for ct, g in c if len(g) >= 3]
    for ct, g in c:
        if 1 <= len(g) <= 2:
            perto = [f for f in fortes if 0 < abs(f - ct) <= NEAR]
            if perto:
                achados.append(('baixa', '—',
                    f"largura {ct}px aparece {len(g)}x, a {abs(perto[0]-ct):.0f}px da largura recorrente {perto[0]}px — provável quase-igual"))

def main():
    args = sys.argv[1:]
    emitir = None
    if '--emitir-tokens' in args:
        k = args.index('--emitir-tokens'); emitir = args[k+1]; del args[k:k+2]
    if not args:
        sys.exit(__doc__)
    telas = carregar(args)
    if not telas:
        sys.exit("nenhuma geometria carregada (rode coletar-geometria.js no navegador primeiro)")

    achados = []
    for t in telas:
        alinhamento(t, achados)
        ritmo(t, achados)
    escala_larguras(telas, achados)

    ordem = {'critica':0, 'alta':1, 'media':2, 'baixa':3}
    achados.sort(key=lambda a: ordem.get(a[0], 9))
    cont = Counter(a[0] for a in achados)

    print("=" * 74)
    print("COERÊNCIA VISUAL — régua inferida do próprio app (sem design system)")
    print("=" * 74)
    print(f"telas: {', '.join(t['screen'] for t in telas)}   ·   elementos medidos: {sum(len(t['items']) for t in telas)}")
    print("desvios: " + " · ".join(f"{cont.get(s,0)} {s}" for s in ('alta','media','baixa')))
    if not achados:
        print("VEREDITO: coerente nos eixos medidos. As telas se alinham à própria régua.")
    else:
        print("VEREDITO: incoerente — o app se contradiz nos pontos abaixo (medido, não opinado).\n")
        atual = None
        for sev, tela, msg in achados:
            if sev != atual:
                print(f"\n--- {sev.upper()} ---"); atual = sev
            print(f"  ✗ [{tela}] {msg}")

    print("\nregra: quase-alinhado (1..8px da linha do app) = defeito; longe = alinhamento próprio,")
    print("       provável decisão, não marcado. Gosto e hierarquia de significado ficam com humano.")
    print("\nMAPA DE COBERTURA")
    print("  COBERTO: " + " · ".join(sorted(set(t['screen'] for t in telas))) +
          " (tema: " + ", ".join(sorted(set(t.get('theme','default') for t in telas))) + ")")
    print("  NÃO COBERTO: telas não coletadas · estados (hover/foco/erro) · mobile · "
          "ícone e hierarquia de significado (não é geometria) · nativo (só web tem geometria exata)")

    if emitir:
        its = [i for t in telas for i in t['items'] if i['W'] < t.get('vw', 99999) - 1]
        regua = {
            "espaco":  [c for c, g in cluster1d([round(i['W']) for i in its], 2) if len(g) >= 3][:8],
            "inferido_de": [t['screen'] for t in telas],
        }
        json.dump(regua, open(emitir, 'w'), ensure_ascii=False, indent=2)
        print(f"\ntokens da régua inferida -> {emitir} (alimenta a v12x-design-audit)")

if __name__ == '__main__':
    main()
