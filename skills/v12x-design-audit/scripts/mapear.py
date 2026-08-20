#!/usr/bin/env python3
"""
v12x-design-audit · motor de mapeamento
--------------------------------------------------------------------------
Compara os valores REALMENTE usados (coletados da tela e/ou do código) com os
tokens do design system, e produz a tabela "valor usado -> token sugerido" com
distância e confiança. É a peça determinística: nenhuma decisão de gosto aqui,
só matemática de proximidade.

- Cor:    ΔE CIEDE2000 em Lab (distância PERCEPTUAL, não a diferença de hex).
          É o que separa "#383838 vs #3A3A3A" (imperceptível) de "#383838 vs
          #4A4A4A" (visível).
- Número: distância absoluta e relativa (raio, espaçamento, tamanho de fonte).
- Fonte:  comparação categórica da família (normalizada).

Uso:
  python3 mapear.py --tokens tokens.json --usados usados.json [--json saida.json]

Formatos aceitos em --tokens: JSON (aninhado ou plano), CSS de custom properties
(:root{--x:#fff}), ou qualquer arquivo de onde extrair hex/px como fallback.
--usados: JSON do coletar-tela.js e/ou do coletar-codigo.sh.

Sem dependências externas — roda com o Python do sistema.
"""
import argparse, json, re, sys, os
from collections import defaultdict

# ---------------------------------------------------------------- cor: utils
NAMED = {  # cores nomeadas que mais aparecem em código legado
    'white': '#ffffff', 'black': '#000000', 'red': '#ff0000', 'blue': '#0000ff',
    'green': '#008000', 'gray': '#808080', 'grey': '#808080', 'silver': '#c0c0c0',
    'transparent': None,
}

def parse_color(v):
    """Devolve (r,g,b) 0-255 ou None se não for cor sólida reconhecível."""
    if not isinstance(v, str): return None
    s = v.strip().lower()
    if s in NAMED:
        s = NAMED[s]
        if s is None: return None
    m = re.fullmatch(r'#([0-9a-f]{3,8})', s)
    if m:
        h = m.group(1)
        if len(h) == 3: h = ''.join(c*2 for c in h)
        if len(h) == 4: h = ''.join(c*2 for c in h[:3])   # #rgba -> ignora alpha
        if len(h) == 8: h = h[:6]                          # #rrggbbaa -> ignora alpha
        if len(h) != 6: return None
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
    m = re.fullmatch(r'rgba?\(([^)]+)\)', s)
    if m:
        parts = re.split(r'[,\s/]+', m.group(1).strip())
        try:
            nums = [p for p in parts if p not in ('', '/')][:3]
            rgb = []
            for p in nums:
                rgb.append(round(float(p[:-1]) * 255 / 100) if p.endswith('%') else int(float(p)))
            if len(rgb) == 3 and all(0 <= c <= 255 for c in rgb): return tuple(rgb)
        except ValueError:
            return None
    return None

def _srgb_to_lab(rgb):
    def lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    x = (r*0.4124564 + g*0.3575761 + b*0.1804375) / 0.95047
    y = (r*0.2126729 + g*0.7151522 + b*0.0721750) / 1.00000
    z = (r*0.0193339 + g*0.1191920 + b*0.9503041) / 1.08883
    def f(t): return t ** (1/3) if t > 216/24389 else (841/108) * t + 4/29
    fx, fy, fz = f(x), f(y), f(z)
    return (116*fy - 16, 500*(fx - fy), 200*(fy - fz))

def delta_e(c1, c2):
    """CIEDE2000. <1 imperceptível · 1-3 sutil · 3-10 distinto · >10 outra cor."""
    import math
    L1, a1, b1 = _srgb_to_lab(c1); L2, a2, b2 = _srgb_to_lab(c2)
    kL = kC = kH = 1.0
    C1 = math.hypot(a1, b1); C2 = math.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cb**7 / (Cb**7 + 25**7))) if Cb > 0 else 0.5
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360 if (a1p or b1) else 0
    h2p = math.degrees(math.atan2(b2, a2p)) % 360 if (a2p or b2) else 0
    dLp = L2 - L1; dCp = C2p - C1p
    if C1p * C2p == 0: dhp = 0
    elif abs(h2p - h1p) <= 180: dhp = h2p - h1p
    elif h2p - h1p > 180: dhp = h2p - h1p - 360
    else: dhp = h2p - h1p + 360
    dHp = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dhp) / 2)
    Lbp = (L1 + L2) / 2; Cbp = (C1p + C2p) / 2
    if C1p * C2p == 0: hbp = h1p + h2p
    elif abs(h1p - h2p) <= 180: hbp = (h1p + h2p) / 2
    elif h1p + h2p < 360: hbp = (h1p + h2p + 360) / 2
    else: hbp = (h1p + h2p - 360) / 2
    T = (1 - 0.17*math.cos(math.radians(hbp-30)) + 0.24*math.cos(math.radians(2*hbp))
         + 0.32*math.cos(math.radians(3*hbp+6)) - 0.20*math.cos(math.radians(4*hbp-63)))
    dTh = 30 * math.exp(-(((hbp - 275) / 25) ** 2))
    Rc = 2 * math.sqrt(Cbp**7 / (Cbp**7 + 25**7)) if Cbp > 0 else 0
    Sl = 1 + (0.015 * (Lbp - 50) ** 2) / math.sqrt(20 + (Lbp - 50) ** 2)
    Sc = 1 + 0.045 * Cbp
    Sh = 1 + 0.015 * Cbp * T
    Rt = -math.sin(math.radians(2 * dTh)) * Rc
    return math.sqrt((dLp/(kL*Sl))**2 + (dCp/(kC*Sc))**2 + (dHp/(kH*Sh))**2
                     + Rt * (dCp/(kC*Sc)) * (dHp/(kH*Sh)))

def to_hex(rgb): return '#%02x%02x%02x' % rgb

# ------------------------------------------------------------- números/fontes
def parse_num(v):
    """px/rem/em -> float em px (rem/em = 16). Devolve None se não for número."""
    if isinstance(v, (int, float)): return float(v)
    if not isinstance(v, str): return None
    s = v.strip().lower()
    m = re.fullmatch(r'(-?\d*\.?\d+)(px|rem|em|%)?', s)
    if not m: return None
    n = float(m.group(1)); u = m.group(2)
    if u in ('rem', 'em'): n *= 16
    elif u == '%': return None
    return n

def norm_font(v):
    """Primeira família da stack, normalizada."""
    if not isinstance(v, str): return None
    first = v.split(',')[0].strip().strip('"\'').lower()
    return re.sub(r'\s+', ' ', first) or None

# ---------------------------------------------------------------- carregar
def flatten(obj, prefix=''):
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = f'{prefix}-{k}' if prefix else str(k)
            if isinstance(v, dict):
                # formato W3C: {"value": "...", "type": "..."}
                if 'value' in v and not isinstance(v['value'], dict):
                    out[key] = v['value']
                else:
                    out.update(flatten(v, key))
            elif isinstance(v, (str, int, float)):
                out[key] = v
    return out

def load_tokens(path):
    txt = open(path, encoding='utf-8').read()
    if path.endswith('.json'):
        try: return flatten(json.loads(txt))
        except json.JSONDecodeError: pass
    toks = {}
    for m in re.finditer(r'(--[A-Za-z0-9_-]+)\s*:\s*([^;}\n]+)', txt):   # CSS vars
        toks[m.group(1)] = m.group(2).strip()
    if toks: return toks
    for m in re.finditer(r'["\']?([A-Za-z0-9_.-]+)["\']?\s*:\s*["\']([^"\']+)["\']', txt):
        toks[m.group(1)] = m.group(2)                                     # JS/TS config
    return toks

def load_usados(paths):
    """Une vários arquivos de coleta. Formato: {prop: {valor: {count, sample}}}"""
    merged = defaultdict(lambda: defaultdict(lambda: {'count': 0, 'onde': []}))
    for p in paths:
        data = json.loads(open(p, encoding='utf-8').read())
        origem = data.get('origem', os.path.basename(p))
        for prop, vals in (data.get('valores') or {}).items():
            for val, info in vals.items():
                if isinstance(info, int): info = {'count': info, 'onde': []}
                slot = merged[prop][val]
                slot['count'] += info.get('count', 1)
                for o in (info.get('onde') or [])[:3]:
                    if o not in slot['onde']: slot['onde'].append(o)
                slot.setdefault('origens', set()).add(origem)
    return merged

# ---------------------------------------------------------------- classificar
def kind_of(prop, value):
    p = prop.lower()
    if 'font-family' in p or p == 'font': return 'fonte'
    if parse_color(value) is not None and ('color' in p or 'background' in p
                                           or 'shadow' in p or 'fill' in p or 'stroke' in p):
        return 'cor'
    if parse_color(value) is not None: return 'cor'
    if parse_num(value) is not None: return 'numero'
    return 'outro'

def bucket(prop):
    p = prop.lower()
    if 'radius' in p: return 'raio'
    if 'font-size' in p: return 'tipografia'
    if any(k in p for k in ('padding', 'margin', 'gap')): return 'espacamento'
    if 'font-family' in p: return 'fonte'
    if 'shadow' in p: return 'sombra'
    if 'color' in p or 'background' in p: return 'cor'
    return 'outro'

def token_candidates(tokens, kind, bkt):
    """Filtra tokens plausíveis para o tipo de valor, pelo NOME e pelo formato."""
    out = []
    for name, raw in tokens.items():
        n = name.lower()
        if kind == 'cor':
            rgb = parse_color(raw)
            if rgb is not None: out.append((name, raw, rgb))
        elif kind == 'numero':
            num = parse_num(raw)
            if num is None: continue
            if bkt == 'raio' and not any(k in n for k in ('radius', 'raio', 'corner', 'round')):
                continue
            if bkt == 'tipografia' and not any(k in n for k in ('font', 'text', 'size', 'type')):
                continue
            if bkt == 'espacamento' and not any(k in n for k in ('space', 'spacing', 'gap', 'size', 'pad', 'margin')):
                continue
            out.append((name, raw, num))
        elif kind == 'fonte':
            f = norm_font(raw)
            if f and any(k in n for k in ('font', 'family', 'type')): out.append((name, raw, f))
    return out

def match(prop, value, tokens):
    """Devolve (token, valor_token, distancia, confianca, nota) ou None."""
    kind = kind_of(prop, value); bkt = bucket(prop)
    cands = token_candidates(tokens, kind, bkt)
    if not cands: return None
    if kind == 'cor':
        rgb = parse_color(value)
        if rgb is None: return None
        best = min(cands, key=lambda c: delta_e(rgb, c[2]))
        d = delta_e(rgb, best[2])
        if d < 0.5:   conf, nota = 'exato', 'idêntico ao token'
        elif d < 1.0: conf, nota = 'alta', 'diferença imperceptível (ΔE<1)'
        elif d < 3.0: conf, nota = 'alta', 'near-miss visível só lado a lado'
        elif d < 10:  conf, nota = 'media', 'cor distinta — confirmar intenção'
        else:         return ('—', '—', d, 'nenhuma', 'sem token próximo (ΔE>10)')
        return (best[0], to_hex(best[2]), round(d, 2), conf, nota)
    if kind == 'numero':
        num = parse_num(value)
        if num is None: return None
        best = min(cands, key=lambda c: abs(num - c[2]))
        d = abs(num - best[2])
        if d == 0:    conf, nota = 'exato', 'já é o token'
        elif d <= 1:  conf, nota = 'alta', f'{d:g}px fora da escala'
        elif d <= 3:  conf, nota = 'media', f'{d:g}px fora da escala'
        else:         return ('—', '—', d, 'nenhuma', f'sem token próximo ({d:g}px)')
        return (best[0], f'{best[2]:g}px', round(d, 2), conf, nota)
    if kind == 'fonte':
        f = norm_font(value)
        if not f: return None
        for name, raw, tf in cands:
            if tf == f: return (name, raw, 0, 'exato', 'família do sistema')
        return ('—', ', '.join(sorted({c[2] for c in cands})), 999, 'nenhuma',
                'família FORA do design system')
    return None

# ---------------------------------------------------------------- severidade
MARCA = ('primary', 'primária', 'primaria', 'brand', 'marca', 'accent', 'cta')
def severidade(bkt, conf, count, onde):
    ctx = ' '.join(onde).lower() if onde else ''
    marca = any(k in ctx for k in MARCA)
    if conf == 'nenhuma':
        if bkt == 'fonte':                 return 'critica'   # fonte fora do sistema é visível
        if marca:                          return 'critica'
        return 'alta'
    if conf == 'exato':                    return None        # conforme, não é achado
    if marca and conf in ('alta', 'media'):return 'alta'
    if count >= 10:                        return 'alta'      # desvio sistemático
    if conf == 'media':                    return 'media'
    return 'baixa'                                            # near-miss isolado

ORDEM = {'critica': 0, 'alta': 1, 'media': 2, 'baixa': 3}
ROTULO = {'critica': 'CRÍTICA', 'alta': 'ALTA', 'media': 'MÉDIA', 'baixa': 'BAIXA'}

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description='Mapeia valores usados -> tokens do design system')
    ap.add_argument('--tokens', required=True)
    ap.add_argument('--usados', required=True, nargs='+')
    ap.add_argument('--json', help='grava a tabela de mapeamento em JSON (para aplicar)')
    ap.add_argument('--min', type=int, default=1, help='ignora valores com menos de N ocorrências')
    a = ap.parse_args()

    tokens = load_tokens(a.tokens)
    if not tokens: sys.exit(f'ERRO: nenhum token lido de {a.tokens}')
    usados = load_usados(a.usados)

    achados, conformes, sem_avaliar = [], 0, []
    for prop, vals in usados.items():
        for val, info in vals.items():
            if info['count'] < a.min: continue
            r = match(prop, val, tokens)
            if r is None:
                sem_avaliar.append((prop, val)); continue
            tok, tokval, dist, conf, nota = r
            sev = severidade(bucket(prop), conf, info['count'], info.get('onde'))
            if sev is None: conformes += 1; continue
            achados.append({'prop': prop, 'valor': val, 'token': tok, 'token_valor': tokval,
                            'distancia': dist, 'confianca': conf, 'nota': nota,
                            'ocorrencias': info['count'], 'onde': info.get('onde', [])[:3],
                            'severidade': sev, 'grupo': bucket(prop)})

    achados.sort(key=lambda x: (ORDEM[x['severidade']], -x['ocorrencias']))
    cont = defaultdict(int)
    for f in achados: cont[f['severidade']] += 1

    print(f"\n{'='*74}\nMAPEAMENTO — valores usados x design system\n{'='*74}")
    print(f"tokens carregados: {len(tokens)}   ·   valores distintos analisados: "
          f"{sum(len(v) for v in usados.values())}   ·   já conformes: {conformes}")
    resumo = ' · '.join(f"{cont[s]} {ROTULO[s].lower()}s" for s in ('critica','alta','media','baixa') if cont[s])
    print(f"fora do sistema: {resumo or 'nenhum'}")
    veredito = ("NÃO aprovar o handoff até resolver as críticas."
                if cont['critica'] else
                "Aprovar com ressalvas — resolver as altas antes de fechar." if cont['alta']
                else "Conforme ao design system nos valores cobertos.")
    print(f"VEREDITO: {veredito}\n")

    atual = None
    for f in achados:
        if f['severidade'] != atual:
            atual = f['severidade']; print(f"\n--- {ROTULO[atual]} ---")
        onde = f"  <- {', '.join(f['onde'])}" if f['onde'] else ''
        seta = f"{f['valor']}  ->  {f['token']} ({f['token_valor']})" if f['token'] != '—' \
               else f"{f['valor']}  ->  SEM TOKEN [{f['token_valor']}]"
        print(f"  [{f['ocorrencias']:>3}x] {f['prop']}: {seta}")
        print(f"        {f['nota']} · confiança {f['confianca']}{onde}")

    if sem_avaliar:
        print(f"\n--- NÃO AVALIADO ({len(sem_avaliar)}) — entra no mapa de cobertura ---")
        for prop, val in sem_avaliar[:12]:
            print(f"  {prop}: {val}")
        if len(sem_avaliar) > 12: print(f"  ... e mais {len(sem_avaliar)-12}")

    print(f"\nRegra: 'exato' e 'alta' são candidatos a troca automática; 'media' e 'nenhuma'\n"
          f"exigem decisão humana (Fase 2 — pode ser one-off proposital).\n")

    if a.json:
        with open(a.json, 'w', encoding='utf-8') as fh:
            json.dump({'veredito': veredito, 'contagem': dict(cont), 'achados': achados,
                       'nao_avaliado': [{'prop': p, 'valor': v} for p, v in sem_avaliar]},
                      fh, ensure_ascii=False, indent=2)
        print(f"tabela de mapeamento -> {a.json}")

if __name__ == '__main__':
    main()
