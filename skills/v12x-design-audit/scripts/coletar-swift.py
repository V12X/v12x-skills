#!/usr/bin/env python3
"""
v12x-design-audit · coletor SWIFT / SwiftUI
---------------------------------------------------------------------------
O coletar-tela.js só funciona onde há navegador. Em app nativo, o CÓDIGO é a
fonte mais fiel: SwiftUI não tem cascata nem herança arbitrária de estilo, então
o valor escrito na view é o valor pintado. A verificação de tela vira captura
(antes/depois), não extração.

Dois modos:
  tokens  <dir-do-design-system>  -> tokens.json   (a norma)
  usados  <dir-do-app>            -> usados.json   (o que as telas usam)

A saída é o mesmo formato do coletar-tela.js, então o mapear.py roda sem mudança.

Conformidade: uma linha que referencia Palette./Layout./Typography./Type. já usa
token — não é achado, e é pulada.
"""
import json, os, re, sys

CONFORME = re.compile(r'\b(Palette|Layout|Typography|Type|Motion|Iconography)\s*\.')

# matizes nomeados do SwiftUI: em sistema acromático, qualquer um é violação
HUES = ('red','blue','green','orange','yellow','purple','pink','mint','teal',
        'cyan','indigo','brown')

def walk(root, skip=()):
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in ('.build','DerivedData','.git','Pods') ]
        if any(s in dp for s in skip): continue
        for f in fn:
            if f.endswith('.swift'): yield os.path.join(dp, f)

def add(val, prop, value, onde):
    # Zero é IDIOMA, não desvio: `HStack(spacing: 0)` significa "sem espaçamento,
    # eu controlo o layout", e `cornerRadius: 0` significa "sem arredondamento".
    # Nenhum design system tem token para a ausência de uma propriedade.
    if isinstance(value, str) and re.fullmatch(r'0(?:\.0+)?px', value):
        return
    d = val.setdefault(prop, {}).setdefault(value, {"count": 0, "onde": []})
    d["count"] += 1
    if len(d["onde"]) < 6 and onde not in d["onde"]: d["onde"].append(onde)

# --------------------------------------------------------------- tokens
def extrair_tokens(design_dir):
    toks = {}
    for path in walk(design_dir):
        base = os.path.basename(path)
        txt = open(path, encoding='utf-8', errors='ignore').read()
        # cor: public static let nome = Color.adaptive(light: Color(hex: 0xRRGGBB
        for m in re.finditer(
            r'(?:public\s+)?static\s+let\s+(\w+)\s*(?::\s*Color\s*)?=\s*Color\.adaptive\(\s*'
            r'light:\s*Color\(hex:\s*(0x[0-9A-Fa-f]{6})', txt):
            toks[f'color-{m.group(1)}'] = '#' + m.group(2)[2:]
        # cor direta: static let nome = Color(hex: 0xRRGGBB
        for m in re.finditer(r'(?:public\s+)?static\s+let\s+(\w+)\s*=\s*Color\(hex:\s*(0x[0-9A-Fa-f]{6})', txt):
            toks.setdefault(f'color-{m.group(1)}', '#' + m.group(2)[2:])
        # pares para teste: static let nomeHex: (...) = (0xRRGGBB, 0xRRGGBB)
        for m in re.finditer(r'static\s+let\s+(\w+)Hex\s*:[^=]*=\s*\(\s*(0x[0-9A-Fa-f]{6})', txt):
            toks.setdefault(f'color-{m.group(1)}', '#' + m.group(2)[2:])
        # números: public static let nome: CGFloat = N
        for m in re.finditer(r'public\s+static\s+let\s+(\w+)\s*:\s*CGFloat\s*=\s*([\d.]+)', txt):
            nome, v = m.group(1), m.group(2)
            grupo = ('radius' if 'radius' in nome.lower() or 'corner' in nome.lower()
                     else 'space' if any(k in nome.lower() for k in
                                         ('spacing','gap','padding','margin')) else 'size')
            toks[f'{grupo}-{nome}'] = f'{float(v):g}px'
        # tipografia: rubik(.face, SIZE, relativeTo:
        for m in re.finditer(r'static\s+let\s+(\w+)\s*=\s*(?:rubik|numeric)\(\s*\.\w+,\s*([\d.]+)', txt):
            toks[f'font-size-{m.group(1)}'] = f'{float(m.group(2)):g}px'
        # família
        for m in re.finditer(r'case\s+\w+\s*=\s*"(Rubik[\w-]*)"', txt):
            toks.setdefault('font-family-rubik', 'Rubik')
    return toks

# --------------------------------------------------------------- usados
def coletar_usados(app_dir, skip):
    val = {}
    arquivos = 0
    for path in walk(app_dir, skip=skip):
        arquivos += 1
        rel = os.path.relpath(path, app_dir)
        for i, line in enumerate(open(path, encoding='utf-8', errors='ignore'), 1):
            s = line.strip()
            if not s or s.startswith('//') or s.startswith('///') or s.startswith('*'):
                continue
            onde = f'{rel}:{i}'
            usa_token = bool(CONFORME.search(s))

            # 1. matiz nomeado (violação de sistema acromático, mesmo "conforme" na linha)
            for h in HUES:
                if re.search(r'(?:Color\.%s\b|\.foregroundColor\(\s*\.%s\b|\.fill\(\s*\.%s\b|'
                             r'\.tint\(\s*\.%s\b|\.background\(\s*\.%s\b)' % (h,h,h,h,h), s):
                    add(val, 'color', h, onde)

            if usa_token:
                continue   # o resto da linha já vem do design system

            # 2. cor hardcoded por hex
            for m in re.finditer(r'Color\(hex:\s*0x([0-9A-Fa-f]{6})', s):
                add(val, 'color', '#' + m.group(1).lower(), onde)
            # 3. branco/preto literais
            for m in re.finditer(r'Color\.(white|black)\b|\.foregroundColor\(\s*\.(white|black)\b', s):
                add(val, 'color', (m.group(1) or m.group(2)), onde)
            # 4. tipografia fora do sistema
            for m in re.finditer(r'\.font\(\s*\.system\(\s*size:\s*([\d.]+)', s):
                add(val, 'font-size', f'{float(m.group(1)):g}px', onde)
            if re.search(r'\.font\(\s*\.(largeTitle|title\d?|headline|subheadline|body|callout|footnote|caption\d?)\b', s):
                add(val, 'font-family', 'sistema (SF Pro)', onde)
            # 5. raio literal
            for m in re.finditer(r'cornerRadius:?\s*\(?\s*([\d.]+)', s):
                add(val, 'border-radius', f'{float(m.group(1)):g}px', onde)
            # 6. espaçamento literal
            for m in re.finditer(r'\.padding\(\s*(?:\.\w+\s*,\s*)?([\d.]+)\s*\)', s):
                add(val, 'padding', f'{float(m.group(1)):g}px', onde)
            for m in re.finditer(r'\bspacing:\s*([\d.]+)', s):
                add(val, 'gap', f'{float(m.group(1)):g}px', onde)
    return val, arquivos

def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    modo, alvo = sys.argv[1], sys.argv[2]
    if modo == 'tokens':
        toks = extrair_tokens(alvo)
        print(json.dumps(toks, ensure_ascii=False, indent=2))
        print(f'\n// {len(toks)} tokens extraídos', file=sys.stderr)
    elif modo == 'usados':
        skip = tuple(sys.argv[3:]) or ('EazyspaceDesign',)
        val, n = coletar_usados(alvo, skip)
        print(json.dumps({"origem": "swift", "arquivos": n, "valores": val},
                         ensure_ascii=False, indent=2))
        print(f'// {n} arquivos .swift varridos (excluindo {", ".join(skip)})', file=sys.stderr)
    else:
        sys.exit(__doc__)

if __name__ == '__main__':
    main()
