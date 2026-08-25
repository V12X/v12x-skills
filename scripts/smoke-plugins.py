#!/usr/bin/env python3
"""
Smoke test de empacotamento dos plugins da V12X.
---------------------------------------------------------------------------
Valida que TODO plugin declarado na marketplace.json instala como plugin de
verdade: manifesto presente, nomes batendo, skill no lugar, comando com corpo.

É o guarda que faltava. O plugin que não instala é a pior falha de reputação
para uma suíte cujo produto é confiança — e o dogfooding pegou isso tarde uma
vez. Nunca mais: isto roda a cada push (ver .github/workflows/plugins.yml).

Sai 0 se tudo passa; 1 listando cada furo. Nenhum furo silencioso.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
erros, avisos, checados = [], [], 0

def frontmatter(path):
    txt = open(path, encoding='utf-8').read()
    m = re.match(r'^---\n(.*?)\n---', txt, re.S)
    fm = {}
    if m:
        for line in m.group(1).splitlines():
            if ':' in line:
                k, v = line.split(':', 1)
                fm[k.strip()] = v.strip()
    return fm, txt

mk_path = os.path.join(ROOT, '.claude-plugin', 'marketplace.json')
if not os.path.isfile(mk_path):
    print("FALHA: .claude-plugin/marketplace.json ausente"); sys.exit(1)
mk = json.load(open(mk_path))

for p in mk.get('plugins', []):
    checados += 1
    nome = p.get('name', '???')
    src = p.get('source', '')
    pdir = os.path.normpath(os.path.join(ROOT, src))
    def erro(msg): erros.append(f"[{nome}] {msg}")

    if not p.get('version'): erro("sem 'version' na marketplace.json")
    if not os.path.isdir(pdir):
        erro(f"source não existe: {src}"); continue

    # 1. manifesto do plugin (o que a doc exige para descobrir commands/)
    pj = os.path.join(pdir, '.claude-plugin', 'plugin.json')
    if not os.path.isfile(pj):
        erro("SEM .claude-plugin/plugin.json — commands/ não será descoberto")
    else:
        try:
            pjd = json.load(open(pj))
            if pjd.get('name') != nome:
                erro(f"plugin.json name='{pjd.get('name')}' != marketplace '{nome}'")
            if not pjd.get('version'):
                avisos.append(f"[{nome}] plugin.json sem 'version'")
        except json.JSONDecodeError as e:
            erro(f"plugin.json inválido: {e}")

    # 2. a skill
    skill = os.path.join(pdir, 'SKILL.md')
    if not os.path.isfile(skill):
        erro("SEM SKILL.md no root do plugin")
    else:
        fm, _ = frontmatter(skill)
        if fm.get('name') != nome:
            erro(f"SKILL.md name='{fm.get('name')}' != plugin '{nome}'")
        if not fm.get('description'):
            erro("SKILL.md sem 'description' (a skill não dispara por descrição)")

    # 3. comandos (se houver): corpo e frontmatter
    cdir = os.path.join(pdir, 'commands')
    if os.path.isdir(cdir):
        cmds = [f for f in os.listdir(cdir) if f.endswith('.md')]
        if not cmds:
            avisos.append(f"[{nome}] commands/ existe mas está vazia")
        for c in cmds:
            fm, txt = frontmatter(os.path.join(cdir, c))
            corpo = txt.split('---', 2)[-1].strip() if txt.count('---') >= 2 else txt.strip()
            if not fm.get('description'):
                erro(f"comando {c} sem 'description'")
            if len(corpo) < 20:
                erro(f"comando {c} sem corpo (não instrui nada)")
            if nome not in txt:
                avisos.append(f"[{nome}] comando {c} não menciona a skill '{nome}'")

    # 4. scripts referenciados no SKILL existem
    if os.path.isfile(skill):
        _, txt = frontmatter(skill)
        for m in re.finditer(r'scripts/([\w.-]+\.(?:sh|py|js))', txt):
            if not os.path.isfile(os.path.join(pdir, 'scripts', m.group(1))):
                erro(f"SKILL.md cita scripts/{m.group(1)} que não existe")

print(f"Plugins verificados: {checados}")
for a in avisos: print(f"  aviso  {a}")
if erros:
    print(f"\nFALHA — {len(erros)} problema(s) de empacotamento:")
    for e in erros: print(f"  ✗ {e}")
    sys.exit(1)
print("OK — todos os plugins instalam como plugin de verdade.")
