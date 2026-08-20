#!/usr/bin/env bash
#
# v12x-design-audit · coletor de CÓDIGO
# -----------------------------------------------------------------------------
# Varre valores visuais HARDCODED no fonte (hex, px, font-family) e emite o
# mesmo JSON do coletar-tela.js — com arquivo:linha em "onde", que é o que
# permite APLICAR a troca depois.
#
# A tela diz a verdade do que é pintado; o código diz onde trocar. Os dois se
# unem pelo valor bruto (#3a3a3a, 7px, Arial) no mapear.py.
#
# Somente leitura. Uso:  bash coletar-codigo.sh [dir] > usados-codigo.json
set -u
ALVO="${1:-.}"
EXCL='node_modules|\.next|dist|build|\.git|vendor|Pods|DerivedData|coverage|\.min\.'

# arquivos de estilo/componente que valem varrer.
# NÃO usar `mapfile` — não existe no bash 3.2 do macOS (falharia em silêncio).
LISTA="$(find "$ALVO" -type f \
  \( -name '*.css' -o -name '*.scss' -o -name '*.sass' -o -name '*.less' \
     -o -name '*.tsx' -o -name '*.jsx' -o -name '*.ts' -o -name '*.js' \
     -o -name '*.vue' -o -name '*.svelte' -o -name '*.html' \) 2>/dev/null \
  | grep -vE "$EXCL")"

set -f; IFS='
'
FILES=$LISTA
set +f; unset IFS

python3 - "$ALVO" $FILES <<'PY'
import json, re, sys, os
alvo = sys.argv[1]
files = [f for f in sys.argv[2:] if f and os.path.isfile(f)]

val = {}
def add(prop, value, onde):
    d = val.setdefault(prop, {}).setdefault(value, {"count": 0, "onde": []})
    d["count"] += 1
    if len(d["onde"]) < 5 and onde not in d["onde"]: d["onde"].append(onde)

# declaração CSS: prop: valor
CSS_DECL = re.compile(r'([a-z-]+)\s*:\s*([^;{}\n]+)', re.I)
INTERESSA = ('color','background','background-color','border-color','font-family',
             'font-size','border-radius','padding','margin','gap','box-shadow',
             'line-height','letter-spacing','border')
# valores soltos em JS/JSX (ex.: color="#3a3a3a", '7px')
HEX  = re.compile(r'#[0-9a-fA-F]{3,8}\b')
FONT = re.compile(r'font-family\s*:\s*([^;{}\n"\']+)', re.I)

# usa token? (var(--x) / theme.x / tokens.x) -> já conforme, não é hardcode
USA_TOKEN = re.compile(r'var\(\s*--|theme\.|tokens?\.|\$[a-z]', re.I)

for f in files:
    try: txt = open(f, encoding='utf-8', errors='ignore').read()
    except Exception: continue
    rel = os.path.relpath(f, alvo)
    for i, line in enumerate(txt.splitlines(), 1):
        s = line.strip()
        if not s or s.startswith(('//', '*', '/*')): continue
        onde = f"{rel}:{i}"
        # declarações CSS-like
        for m in CSS_DECL.finditer(s):
            prop, raw = m.group(1).lower(), m.group(2).strip().rstrip(',')
            if prop not in INTERESSA: continue
            if USA_TOKEN.search(raw): continue            # já usa token — conforme
            if prop == 'font-family':
                add('font-family', raw.strip('"\''), onde); continue
            # normaliza shorthand pegando o primeiro valor significativo
            first = raw.split()[0] if raw.split() else raw
            if HEX.fullmatch(first) or re.fullmatch(r'-?\d*\.?\d+(px|rem|em)', first):
                p = {'background':'background-color','border':'border-top-width'}.get(prop, prop)
                if prop == 'border-radius': p = 'border-top-left-radius'
                if prop in ('padding','margin'): p = f'{prop}-top'
                add(p, first, onde)
            elif HEX.search(raw):
                add(prop if 'color' in prop else 'color', HEX.search(raw).group(0), onde)
        # hex solto fora de declaração (props de componente, objetos de estilo)
        if not CSS_DECL.search(s):
            for h in HEX.findall(s)[:2]:
                if not USA_TOKEN.search(s): add('color', h, onde)

print(json.dumps({"origem": "codigo", "arquivos": len(files), "valores": val},
                 ensure_ascii=False, indent=2))
PY
