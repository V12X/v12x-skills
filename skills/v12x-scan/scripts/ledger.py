#!/usr/bin/env python3
# v12x-scan · scripts/ledger.py — ledger de cobertura por unidade de superfície
# -----------------------------------------------------------------------------
# "Nenhum furo silencioso", verificável por máquina. A auditoria não decide o que
# cobrir de memória: as UNIDADES vêm do código, por enumeração determinística —
# cada tabela, cada policy (tabela × operação), cada função SQL (definer marcada),
# cada Edge Function, cada bucket, cada rota, cada workflow, cada URL scheme — e
# cada unidade termina a auditoria com UM estado. Unidade sem estado é furo.
#
# Caso real que motivou isto: uma policy de INSERT da migration 0001 deixava
# qualquer conta se inserir numa organização como admin. Quatro auditorias
# leram "as migrations recentes" e marcaram RLS como coberta. O ledger teria
# mostrado: `members · INSERT · lido em: nunca`.
#
# Estados:  planejado · coberto · amostrado · fora-de-escopo · adiado · pendente
#   coberto / amostrado exigem "lido em" (commit) — é o que permite reabrir por diff.
#   fora-de-escopo é o que a rodada decidiu não olhar (e diz). Nunca vira coberto
#   por omissão. adiado leva motivo na nota. pendente = depende de fato fora do repo.
#
# Uso:
#   ledger.py rascunho <alvo> [--anterior .security-ledger.md] [--saida arquivo]
#       enumera as unidades e, se houver ledger anterior, HERDA os estados cuja
#       fonte não mudou (git diff <commit>..HEAD -- origem) e reabre as que mudaram.
#   ledger.py marcar <ledger> <id|/regex/> <estado> [--nota "..."] [--commit X]
#       marca uma unidade (por id) ou várias (regex sobre tipo+unidade); para
#       coberto/amostrado grava "lido em" = commit (padrão: HEAD do alvo).
#   ledger.py validar <ledger> [--escopo /regex/] [--final]
#       todo estado válido; coberto/amostrado com commit; com --escopo, nada fora
#       do escopo pode estar coberto/amostrado; com --final, nenhum planejado.
#       Sai com 1 se violar — serve de portão no CI.
#
# Só lê o repositório. Escreve apenas o arquivo de saída. Sem dependências.
# -----------------------------------------------------------------------------
from __future__ import annotations
import argparse, hashlib, os, re, subprocess, sys
from pathlib import Path

ESTADOS = ('planejado', 'coberto', 'amostrado', 'fora-de-escopo', 'adiado', 'pendente')
IGNORAR_DIRS = {'node_modules', '.git', '.build', 'build', 'dist', 'DerivedData', 'Pods',
                'vendor', '.next', '.vercel', 'coverage', '__pycache__'}

# ------------------------------------------------------------------ util ----

def rel(p: Path, raiz: Path) -> str:
    try: return str(p.relative_to(raiz))
    except ValueError: return str(p)

def uid(tipo: str, unidade: str) -> str:
    """id estável entre rodadas: prefixo do tipo + hash curto de (tipo, unidade)."""
    h = hashlib.sha1(f'{tipo}\x00{unidade}'.encode()).hexdigest()[:5]
    return f'{tipo[:3]}-{h}'

def git(raiz: Path, *args: str) -> str:
    try:
        return subprocess.run(['git', '-C', str(raiz), *args], capture_output=True,
                              text=True, check=False).stdout.strip()
    except FileNotFoundError:
        return ''

def arquivos(raiz: Path, sufixos: tuple[str, ...], sob: str | None = None):
    base = raiz / sob if sob else raiz
    if not base.exists(): return
    for dp, dns, fns in os.walk(base):
        dns[:] = [d for d in dns if d not in IGNORAR_DIRS]
        for f in sorted(fns):
            if f.endswith(sufixos): yield Path(dp) / f

def sem_comentarios_sql(sql: str) -> str:
    return re.sub(r'--[^\n]*', '', sql)

def linha_de(texto: str, pos: int) -> int:
    return texto.count('\n', 0, pos) + 1

# ------------------------------------------------------------ enumeração ----
# Cada enumerador devolve lista de dicts: tipo, unidade, origem, nota.
# Para SQL, a ORDEM das migrations importa: a última definição vale, e drop remove.

def _tipos_params(lista: str) -> tuple[str, ...]:
    """'p_id uuid, p_n int default 0, variadic x text[]' -> ('uuid','int','text[]').
    Também aceita só tipos, como em DROP FUNCTION f(uuid, text)."""
    partes, nivel, atual = [], 0, ''
    for ch in lista:
        if ch in '([': nivel += 1
        if ch in ')]': nivel -= 1
        if ch == ',' and nivel == 0: partes.append(atual); atual = ''
        else: atual += ch
    partes.append(atual)
    tipos = []
    for parte in partes:
        parte = re.split(r'\s+default\s+|\s*=\s*', parte.strip(), 1, flags=re.I)[0].strip()
        if not parte: continue
        toks = re.sub(r'^(in|out|inout|variadic)\s+', '', parte, flags=re.I).split()
        tipo = ' '.join(toks[1:]) if len(toks) >= 2 and not re.match(r'^(timestamp|double|character|bit)$', toks[0], re.I) else ' '.join(toks)
        tipos.append(re.sub(r'^public\.', '', tipo.lower()).replace(' ', ''))
    return tuple(tipos)

def enum_sql(raiz: Path):
    """tabelas, policies (tabela × op), funções (chave nome+aridade; definer marcada),
    buckets — replay das migrations em ordem de arquivo E de posição dentro do arquivo.
    create define, drop remove, replace sobrescreve; alter/grant/revoke tocam a origem
    (é o toque que a reabertura por diff precisa ver)."""
    tabelas: dict = {}; policies: dict = {}; funcoes: dict = {}; buckets: dict = {}
    nome = lambda s: re.sub(r'^(public|auth|storage)\.', '', s.replace('"', '')).lower()
    mig_dirs = [d for d in (raiz / 'supabase' / 'migrations', raiz / 'migrations',
                            raiz / 'db' / 'migrations') if d.is_dir()]
    RX = [
      ('create_table', re.compile(r'\bcreate\s+table\s+(?:if\s+not\s+exists\s+)?([\w."]+)', re.I)),
      ('drop_table',   re.compile(r'\bdrop\s+table\s+(?:if\s+exists\s+)?([\w."]+)', re.I)),
      ('touch_table',  re.compile(r'\b(?:alter\s+table\s+(?:if\s+exists\s+)?(?:only\s+)?|(?:grant|revoke)\s+[^;]*?\bon\s+(?:table\s+)?)([\w."]+)', re.I)),
      ('create_policy', re.compile(r'\bcreate\s+policy\s+("[^"]+"|\w+)\s+on\s+([\w."]+)((?:(?!\bcreate\s+policy\b)[\s\S]){0,400}?)(?=;|\bcreate\s+policy\b)', re.I)),
      ('drop_policy',  re.compile(r'\bdrop\s+policy\s+(?:if\s+exists\s+)?("[^"]+"|\w+)\s+on\s+([\w."]+)', re.I)),
      ('alter_policy', re.compile(r'\balter\s+policy\s+("[^"]+"|\w+)\s+on\s+([\w."]+)', re.I)),
      ('create_fn',    re.compile(r'\bcreate\s+(?:or\s+replace\s+)?function\s+([\w."]+)\s*\(', re.I)),
      ('drop_fn',      re.compile(r'\bdrop\s+function\s+(?:if\s+exists\s+)?([\w."]+)\s*(\([^)]*\))?', re.I)),
      ('bucket',       re.compile(r"insert\s+into\s+storage\.buckets[^;]*?values\s*\(\s*'([^']+)'", re.I | re.S)),
    ]
    for d in mig_dirs:
        for f in sorted(d.glob('*.sql')):
            sql = sem_comentarios_sql(f.read_text(errors='replace'))
            eventos = []
            for kind, rx in RX:
                for m in rx.finditer(sql): eventos.append((m.start(), kind, m))
            eventos.sort(key=lambda e: e[0])
            for pos, kind, m in eventos:
                origem = f'{rel(f, raiz)}:{linha_de(sql, pos)}'
                if kind == 'create_table': tabelas[nome(m.group(1))] = {'origem': origem}
                elif kind == 'drop_table': tabelas.pop(nome(m.group(1)), None)
                elif kind == 'touch_table':
                    t = nome(m.group(1))
                    if t in tabelas: tabelas[t]['origem'] = origem
                elif kind == 'create_policy':
                    pn = m.group(1).strip('"'); t = nome(m.group(2))
                    fm = re.search(r'\bfor\s+(select|insert|update|delete|all)\b', m.group(3), re.I)
                    policies[(t, pn)] = {'op': (fm.group(1) if fm else 'all').upper(), 'origem': origem}
                elif kind == 'drop_policy': policies.pop((nome(m.group(2)), m.group(1).strip('"')), None)
                elif kind == 'alter_policy':
                    k = (nome(m.group(2)), m.group(1).strip('"'))
                    if k in policies: policies[k]['origem'] = origem
                elif kind == 'create_fn':
                    fn = nome(m.group(1))
                    # parâmetros: do '(' até o ')' que fecha, respeitando aninhamento
                    i, nivel = m.end(), 1
                    while i < len(sql) and nivel: nivel += {'(': 1, ')': -1}.get(sql[i], 0); i += 1
                    tipos = _tipos_params(sql[m.end():i - 1])
                    a = re.compile(r'\$(\w*)\$').search(sql, i)
                    definer = False
                    if a:
                        tag = a.group(0); fimc = sql.find(tag, a.end())
                        if fimc >= 0:
                            pv = sql.find(';', fimc + len(tag))
                            decl = sql[m.start():a.start()] + sql[fimc + len(tag):pv if pv > 0 else None]
                            definer = bool(re.search(r'security\s+definer', decl, re.I))
                    funcoes[(fn, len(tipos))] = {'origem': origem, 'definer': definer, 'tipos': tipos}
                elif kind == 'drop_fn':
                    fn = nome(m.group(1))
                    if m.group(2):
                        funcoes.pop((fn, len(_tipos_params(m.group(2)[1:-1]))), None)
                    else:
                        for k in [k for k in funcoes if k[0] == fn]: funcoes.pop(k)
                elif kind == 'bucket': buckets[m.group(1)] = {'origem': origem}

    # policies quase homônimas na mesma tabela × operação: um replace que mirou o nome errado
    # (acento, caixa) e `drop ... if exists` engoliu. Caso real: 0065 dropou "proprio", a da
    # 0001 ("próprio") sobreviveu, e o endurecimento nunca entrou em vigor (policies somam por OR).
    import unicodedata
    def chave_frouxa(s: str) -> str:
        return ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c)).lower().strip()
    grupos: dict = {}
    for (t, pn), v in policies.items():
        grupos.setdefault((t, v['op'], chave_frouxa(pn)), []).append(pn)
    quase: dict = {}
    for (t, op, _), nomes in grupos.items():
        if len(nomes) > 1:
            for pn in nomes:
                outros = ', '.join(f'"{o}"' for o in nomes if o != pn)
                quase[(t, pn)] = f'quase homônima de {outros} na mesma operação — replace que falhou?'

    out = []
    for t, v in sorted(tabelas.items()):
        out.append({'tipo': 'tabela', 'unidade': t, 'origem': v['origem'], 'nota': ''})
    for (t, p), v in sorted(policies.items()):
        out.append({'tipo': 'policy', 'unidade': f'{t} · {v["op"]} · "{p}"', 'origem': v['origem'], 'nota': quase.get((t, p), '')})
    for (fn, n), v in sorted(funcoes.items()):
        out.append({'tipo': 'função', 'unidade': f'{fn}({", ".join(v["tipos"])})', 'origem': v['origem'],
                    'nota': 'security definer' if v['definer'] else ''})
    for b, v in sorted(buckets.items()):
        out.append({'tipo': 'bucket', 'unidade': b, 'origem': v['origem'], 'nota': ''})
    return out

def enum_edge(raiz: Path):
    out = []
    base = raiz / 'supabase' / 'functions'
    if not base.is_dir(): return out
    for d in sorted(p for p in base.iterdir() if p.is_dir() and not p.name.startswith('_')):
        entrada = next((d / n for n in ('index.ts', 'index.js', 'main.ts') if (d / n).exists()), d)
        out.append({'tipo': 'edge', 'unidade': d.name, 'origem': rel(entrada, raiz), 'nota': ''})
    return out

ROTA_PADROES = [
    # Express / Hono / Fastify / Koa-router:  app.get('/x',  router.post("/y"
    (r'\b[\w.]+\.(get|post|put|patch|delete|all)\s*\(\s*[\'"`](/[^\'"`]*)', ('ts', 'js', 'mjs', 'tsx')),
    # FastAPI / Flask:  @app.get("/x")  @router.post('/y')  @app.route('/z', methods=[...])
    (r'@\w+\.(get|post|put|patch|delete|route)\s*\(\s*[\'"]([^\'"]+)', ('py',)),
    # Go net/http / chi / gin:  HandleFunc("/x"  r.GET("/y"
    (r'\.(?:HandleFunc|Handle|GET|POST|PUT|PATCH|DELETE)\s*\(\s*"([^"]+)"', ('go',)),
    # Rails:  get '/x'  post "/y"  resources :z
    (r'^\s*(get|post|put|patch|delete|resources)\s+[\'":]([\w/:#]+)', ('rb',)),
]

def enum_rotas(raiz: Path):
    out, vistos = [], set()
    # arquivos-rota por convenção (Next.js app router, pages/api, Vercel api/)
    for f in arquivos(raiz, ('.ts', '.js', '.tsx', '.mjs')):
        r = rel(f, raiz)
        if re.search(r'(^|/)app/.*/route\.(ts|js)$', r) or re.search(r'(^|/)pages/api/', r) \
           or re.match(r'(^|.*/)api/[^/]+\.(ts|js|mjs)$', r):
            u = re.sub(r'/route\.(ts|js)$', '', r).replace('pages/api', 'api')
            if u not in vistos:
                vistos.add(u); out.append({'tipo': 'rota', 'unidade': u, 'origem': r, 'nota': 'por convenção de arquivo'})
    # rotas declaradas em código
    for padrao, exts in ROTA_PADROES:
        rx = re.compile(padrao, re.I | re.M)
        for f in arquivos(raiz, tuple('.' + e for e in exts)):
            try: texto = f.read_text(errors='replace')
            except OSError: continue
            for m in rx.finditer(texto):
                g = m.groups()
                metodo, caminho = (g[0].upper(), g[1]) if len(g) == 2 else ('*', g[0])
                u = f'{metodo} {caminho}'
                chave = (u, rel(f, raiz))
                if chave in vistos: continue
                vistos.add(chave)
                out.append({'tipo': 'rota', 'unidade': u, 'origem': f'{rel(f, raiz)}:{linha_de(texto, m.start())}', 'nota': ''})
    return out

def enum_ci(raiz: Path):
    base = raiz / '.github' / 'workflows'
    if not base.is_dir(): return []
    return [{'tipo': 'workflow', 'unidade': f.name, 'origem': rel(f, raiz), 'nota': ''}
            for f in sorted(base.glob('*.y*ml'))]

def enum_deeplinks(raiz: Path):
    out = []
    for f in arquivos(raiz, ('Info.plist',)):
        texto = f.read_text(errors='replace')
        if 'CFBundleURLSchemes' not in texto: continue
        bloco = texto.split('CFBundleURLSchemes', 1)[1]
        for s in re.findall(r'<string>([^<]+)</string>', bloco.split('</array>', 1)[0]):
            out.append({'tipo': 'deeplink', 'unidade': f'{s}://', 'origem': rel(f, raiz), 'nota': ''})
    return out

def enumerar(raiz: Path):
    unidades = []
    for fn in (enum_sql, enum_edge, enum_rotas, enum_ci, enum_deeplinks):
        unidades.extend(fn(raiz))
    for u in unidades:
        u['id'] = uid(u['tipo'], u['unidade']); u['estado'] = 'planejado'; u['lido_em'] = ''
    return unidades

# ---------------------------------------------------------- ledger (md) ----

CABECALHO = '| id | tipo | unidade | origem | estado | lido em | nota |'
SEPARADOR = '|---|---|---|---|---|---|---|'

def ler_ledger(p: Path) -> tuple[list[dict], list[str]]:
    """devolve (linhas-unidade, texto-fora-da-tabela). Só linhas `| id | ...` com 7 colunas."""
    unidades, outras = [], []
    for linha in p.read_text().splitlines():
        if linha.startswith('|') and linha.count('|') >= 8 and not linha.startswith('|---') \
           and not linha.startswith('| id |'):
            c = [x.strip() for x in linha.strip().strip('|').split('|')]
            unidades.append({'id': c[0], 'tipo': c[1], 'unidade': c[2], 'origem': c[3],
                             'estado': c[4], 'lido_em': c[5], 'nota': c[6] if len(c) > 6 else ''})
        else:
            outras.append(linha)
    return unidades, outras

def escrever_ledger(p: Path, unidades: list[dict], raiz: Path, removidas: list[dict] | None = None):
    hoje = subprocess.run(['date', '+%Y-%m-%d'], capture_output=True, text=True).stdout.strip()
    head = git(raiz, 'rev-parse', '--short', 'HEAD') or 'sem git'
    contagem = {e: sum(1 for u in unidades if u['estado'] == e) for e in ESTADOS}
    linhas = [
        '# Ledger de cobertura · v12x-scan',
        '',
        f'Gerado em {hoje} · commit {head} · {len(unidades)} unidades.',
        'Estados: ' + ' · '.join(f'{e} {n}' for e, n in contagem.items() if n),
        '',
        'Regras: toda unidade termina com um estado. `coberto`/`amostrado` exigem `lido em` (commit).',
        'Rodada com escopo marca o resto `fora-de-escopo`, nunca `coberto`. `adiado` leva motivo.',
        'Na próxima auditoria, `ledger.py rascunho --anterior` herda o que não mudou e reabre o que mudou.',
        '',
        CABECALHO, SEPARADOR,
    ]
    for u in unidades:
        linhas.append(f'| {u["id"]} | {u["tipo"]} | {u["unidade"]} | {u["origem"]} | {u["estado"]} | {u["lido_em"]} | {u["nota"]} |')
    if removidas:
        linhas += ['', '## Removidas desde o ledger anterior (não enumeradas nesta rodada)', '']
        for u in removidas:
            linhas.append(f'- `{u["id"]}` {u["tipo"]} · {u["unidade"]} · estava `{u["estado"]}`')
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text('\n'.join(linhas) + '\n')

# ------------------------------------------------------------ comandos ----

def cmd_rascunho(a):
    raiz = Path(a.alvo).resolve()
    atuais = enumerar(raiz)
    anterior = Path(a.anterior) if a.anterior else raiz / '.security-ledger.md'
    removidas = []
    if anterior.exists():
        antigas, _ = ler_ledger(anterior)
        por_chave = {(u['tipo'], u['unidade']): u for u in antigas}
        herdadas = reabertas = 0
        for u in atuais:
            v = por_chave.pop((u['tipo'], u['unidade']), None)
            if not v: u['nota'] = (u['nota'] + ' · ' if u['nota'] else '') + 'novo'; continue
            if v['estado'] in ('coberto', 'amostrado') and v['lido_em']:
                arq = u['origem'].split(':')[0]
                diff = subprocess.run(['git', '-C', str(raiz), 'diff', '--quiet', v['lido_em'], 'HEAD', '--', arq],
                                      capture_output=True)
                if diff.returncode == 0:
                    u['estado'], u['lido_em'], u['nota'] = v['estado'], v['lido_em'], v['nota']; herdadas += 1
                else:
                    u['estado'] = 'planejado'; u['lido_em'] = ''
                    u['nota'] = f'fonte mudou desde {v["lido_em"]} (era {v["estado"]})'; reabertas += 1
            elif v['estado'] in ('fora-de-escopo', 'adiado', 'pendente'):
                u['estado'], u['lido_em'], u['nota'] = v['estado'], v['lido_em'], v['nota']; herdadas += 1
            else:
                u['nota'] = v['nota']
        removidas = list(por_chave.values())
        print(f'ledger anterior: {anterior} · herdadas {herdadas} · reabertas por diff {reabertas} · '
              f'novas {sum(1 for u in atuais if "novo" in u["nota"])} · removidas {len(removidas)}')
    saida = Path(a.saida) if a.saida else raiz / '.security-reports' / 'ledger.md'
    escrever_ledger(saida, atuais, raiz, removidas)
    por_tipo: dict[str, int] = {}
    for u in atuais: por_tipo[u['tipo']] = por_tipo.get(u['tipo'], 0) + 1
    print(f'{len(atuais)} unidades → {saida}')
    print('  ' + ' · '.join(f'{t} {n}' for t, n in sorted(por_tipo.items())))
    definers = sum(1 for u in atuais if u['tipo'] == 'função' and 'definer' in u['nota'])
    if definers: print(f'  (funções security definer: {definers} — cada uma é para abrir)')
    plan = sum(1 for u in atuais if u['estado'] == 'planejado')
    print(f'  planejado: {plan} — a auditoria termina quando for zero (ou fora-de-escopo/adiado com motivo)')

def cmd_marcar(a):
    p = Path(a.ledger)
    unidades, _ = ler_ledger(p)
    if a.estado not in ESTADOS: sys.exit(f'estado inválido: {a.estado} (use {", ".join(ESTADOS)})')
    raiz = p.resolve().parent
    while raiz != raiz.parent and not (raiz / '.git').exists(): raiz = raiz.parent
    commit = a.commit or git(raiz, 'rev-parse', '--short', 'HEAD')
    if a.alvo.startswith('/') and a.alvo.endswith('/') and len(a.alvo) > 2:
        rx = re.compile(a.alvo[1:-1], re.I)
        alvo = [u for u in unidades if rx.search(f'{u["tipo"]} {u["unidade"]} {u["origem"]}')]
    else:
        alvo = [u for u in unidades if u['id'] == a.alvo]
    if not alvo: sys.exit(f'nenhuma unidade casa com {a.alvo}')
    if a.estado == 'adiado' and not a.nota: sys.exit('adiado exige --nota com o motivo')
    for u in alvo:
        u['estado'] = a.estado
        u['lido_em'] = commit if a.estado in ('coberto', 'amostrado') else ''
        if a.nota: u['nota'] = a.nota
    # reescreve só a tabela, preservando o resto do arquivo
    texto = p.read_text().splitlines()
    por_id = {u['id']: u for u in unidades}
    novo = []
    for linha in texto:
        if linha.startswith('|') and not linha.startswith('|---') and not linha.startswith('| id |'):
            i = linha.strip().strip('|').split('|')[0].strip()
            u = por_id.get(i)
            if u:
                novo.append(f'| {u["id"]} | {u["tipo"]} | {u["unidade"]} | {u["origem"]} | {u["estado"]} | {u["lido_em"]} | {u["nota"]} |'); continue
        novo.append(linha)
    p.write_text('\n'.join(novo) + '\n')
    print(f'{len(alvo)} unidade(s) → {a.estado}' + (f' (lido em {commit})' if a.estado in ('coberto', 'amostrado') else ''))

def cmd_validar(a):
    unidades, _ = ler_ledger(Path(a.ledger))
    erros = []
    rx = re.compile(a.escopo[1:-1], re.I) if a.escopo else None
    for u in unidades:
        if u['estado'] not in ESTADOS:
            erros.append(f'{u["id"]} estado inválido: "{u["estado"]}"'); continue
        if u['estado'] in ('coberto', 'amostrado') and not re.fullmatch(r'[0-9a-f]{7,40}', u['lido_em']):
            erros.append(f'{u["id"]} {u["estado"]} sem "lido em" (commit) — coberto sem prova é só uma palavra')
        if u['estado'] == 'adiado' and not u['nota']:
            erros.append(f'{u["id"]} adiado sem motivo na nota')
        if rx and not rx.search(f'{u["tipo"]} {u["unidade"]} {u["origem"]}') and u['estado'] in ('coberto', 'amostrado'):
            erros.append(f'{u["id"]} fora do escopo /{a.escopo[1:-1]}/ mas marcada {u["estado"]} — escopo marca fora-de-escopo, nunca coberto')
        if a.final and u['estado'] == 'planejado':
            erros.append(f'{u["id"]} ainda planejado no fim: {u["tipo"]} · {u["unidade"]} — é furo silencioso')
    contagem = {e: sum(1 for u in unidades if u['estado'] == e) for e in ESTADOS}
    print(f'{len(unidades)} unidades · ' + ' · '.join(f'{e} {n}' for e, n in contagem.items() if n))
    if erros:
        print(f'\n{len(erros)} violação(ões):'); [print('  ' + e) for e in erros]; sys.exit(1)
    print('ledger válido.')

def main():
    ap = argparse.ArgumentParser(description='ledger de cobertura por unidade de superfície (v12x-scan)')
    sp = ap.add_subparsers(dest='cmd', required=True)
    r = sp.add_parser('rascunho'); r.add_argument('alvo', nargs='?', default='.')
    r.add_argument('--anterior'); r.add_argument('--saida'); r.set_defaults(fn=cmd_rascunho)
    m = sp.add_parser('marcar'); m.add_argument('ledger'); m.add_argument('alvo', help='id ou /regex/')
    m.add_argument('estado'); m.add_argument('--nota', default=''); m.add_argument('--commit'); m.set_defaults(fn=cmd_marcar)
    v = sp.add_parser('validar'); v.add_argument('ledger'); v.add_argument('--escopo', help='/regex/')
    v.add_argument('--final', action='store_true'); v.set_defaults(fn=cmd_validar)
    a = ap.parse_args(); a.fn(a)

if __name__ == '__main__':
    main()
