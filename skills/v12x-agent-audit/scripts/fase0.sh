#!/usr/bin/env bash
#
# v12x-agent-audit · Fase 0 — extrair a superfície de um agente / servidor MCP / skill
# -----------------------------------------------------------------------------
# Mapeia o que o componente EXPÕE, sem executá-lo: definição, ferramentas e suas
# descrições, texto escondido, poderes perigosos, permissões pedidas e proveniência.
# Degrada com elegância quando falta ferramenta (cada ausência vira "NÃO COBERTO")
# e imprime o mapa de cobertura no fim.
#
# Somente leitura. Não instala, não roda o servidor, não executa scripts do alvo.
#
# Uso:
#   bash fase0.sh [dir-alvo]        # padrão: diretório atual
#
# Compatível com o bash 3.2 do macOS. Sem `set -e` (grep sem match retorna 1).

set -u

ALVO="${1:-.}"
COB=""; GAP=""
cob(){ COB="$COB\n  $1"; }
gap(){ GAP="$GAP\n  $1"; }
have(){ command -v "$1" >/dev/null 2>&1; }
titulo(){ printf '\n== %s ==\n' "$1"; }
gr(){ grep -rnE "$1" --include='*.ts' --include='*.js' --include='*.py' --include='*.json' "$ALVO" 2>/dev/null | grep -v node_modules; }

titulo "Âncora"
COMMIT="$(git -C "$ALVO" rev-parse --short HEAD 2>/dev/null)"
[ -n "$COMMIT" ] && [ "$COMMIT" != "HEAD" ] || COMMIT="sem commit/git"
echo "alvo:   $ALVO"
echo "commit: $COMMIT"
echo "data:   $(date '+%Y-%m-%d %H:%M')"

# ---- 1. definição do componente ---------------------------------------------
titulo "Definição do componente"
DEF="$(find "$ALVO" -maxdepth 3 \
  \( -name 'server.json' -o -name 'mcp.json' -o -name '*.mcp.json' -o -name '.mcp.json' \
     -o -name 'manifest.json' -o -name 'SKILL.md' -o -name 'package.json' \) \
  -not -path '*/node_modules/*' 2>/dev/null)"
if [ -n "$DEF" ]; then echo "$DEF"; cob "definição localizada"; else
  echo "nenhum manifesto/definição encontrado — alvo pode ser binário ou fonte parcial"
  gap "definição do componente (não localizada)"
fi

# ---- 2. ferramentas e descrições (onde mora o tool poisoning) ---------------
titulo "Ferramentas e descrições declaradas"
TOOLS="$(gr '(name|description|title)\s*[:=]\s*["'\'']' | grep -iE 'tool|description|inputschema|name' | head -50)"
if [ -n "$TOOLS" ]; then echo "$TOOLS"; echo "-> LER cada descrição: ela entra no prompt do agente"; cob "ferramentas/descrições extraídas"
else echo "nenhuma descrição de ferramenta detectada por padrão"; gap "descrições de ferramenta (não detectadas)"; fi

# ---- 3. texto escondido nas descrições (ASCII smuggling) --------------------
# grep -P (PCRE) não existe no BSD grep do macOS — cair para perl, depois python3.
titulo "Texto escondido / caracteres invisíveis"
INVIS_RE='[\x{200B}-\x{200F}\x{202A}-\x{202E}\x{2060}\x{FEFF}\x{E0000}-\x{E007F}]'
find_src(){ find "$ALVO" \( -name '*.ts' -o -name '*.js' -o -name '*.py' -o -name '*.json' -o -name '*.md' \) \
            -not -path '*/node_modules/*' 2>/dev/null; }
scan_invis(){
  local hits=""
  if echo | grep -qP 'x' 2>/dev/null; then
    hits="$(grep -rlP "$INVIS_RE" --include='*.ts' --include='*.js' --include='*.py' \
            --include='*.json' --include='*.md' "$ALVO" 2>/dev/null | grep -v node_modules)"
    echo "__ok__$hits"; return
  fi
  if have perl; then
    hits="$(find_src | while read -r f; do
              perl -CSD -ne 'BEGIN{$m=0} $m=1 if /[\x{200B}-\x{200F}\x{202A}-\x{202E}\x{2060}\x{FEFF}\x{E0000}-\x{E007F}]/; END{print "'"$f"'\n" if $m}' "$f" 2>/dev/null
            done)"
    echo "__ok__$hits"; return
  fi
  if have python3; then
    hits="$(python3 - "$ALVO" <<'PY' 2>/dev/null
import os,sys,re
bad=re.compile('[​-‏‪-‮⁠﻿\U000e0000-\U000e007f]')
root=sys.argv[1]; ext=('.ts','.js','.py','.json','.md')
for dp,dn,fn in os.walk(root):
    if 'node_modules' in dp: continue
    for f in fn:
        if f.endswith(ext):
            p=os.path.join(dp,f)
            try:
                if bad.search(open(p,encoding='utf-8',errors='ignore').read()): print(p)
            except Exception: pass
PY
)"
    echo "__ok__$hits"; return
  fi
  echo "__nocov__"
}
RES="$(scan_invis)"
if [ "$RES" = "__nocov__" ]; then
  echo "grep -P, perl e python3 todos ausentes — varredura não rodou"
  gap "caracteres invisíveis (nenhum motor disponível)"
else
  HITS="${RES#__ok__}"
  if [ -n "$HITS" ]; then
    echo "$HITS"
    echo "^ ARQUIVOS COM INVISÍVEIS — texto oculto não tem uso legítimo (Alto/Crítico)"
    cob "varredura de caracteres invisíveis (achou)"
  else
    echo "nenhum caractere invisível encontrado"
    cob "varredura de caracteres invisíveis (limpo)"
  fi
fi

# ---- 4. instrução dirigida ao modelo dentro de descrições/prompts -----------
titulo "Linguagem imperativa dirigida ao modelo"
INJ="$(grep -rniE '(antes de (usar|chamar)|ignore (the|all|previous)|disregard|you must (first|always)|always (read|include|call)|do not (tell|mention|reveal)|system prompt|<important>|<system>)' \
  --include='*.ts' --include='*.js' --include='*.py' --include='*.json' --include='*.md' "$ALVO" 2>/dev/null | grep -v node_modules | head -20)"
if [ -n "$INJ" ]; then echo "$INJ"; echo "-> ler intenção: empurra o modelo além do que a ferramenta promete?"; cob "varredura de instrução dirigida"
else echo "nenhum padrão de instrução dirigida encontrado"; cob "instrução dirigida (limpo)"; fi

# ---- 5. poderes perigosos no executor ---------------------------------------
titulo "Poderes perigosos (executor)"
show(){ local r="$1" lbl="$2"; local o; o="$(gr "$r" | head -12)"; [ -n "$o" ] && { echo "-- $lbl --"; echo "$o"; }; }
show '(child_process|exec\(|execSync|spawn|os\.system|subprocess|Deno\.run)' 'shell / exec'
show '(fetch|axios|http\.request|requests\.(get|post)|urllib)' 'rede / canal de saída'
show '(\.ssh|id_rsa|\.aws|/etc/passwd|os\.environ|process\.env)' 'leitura de credencial / env'
show '(readFile|writeFile|unlink|open\(|Path\()\s*\(?\s*(args|params|input|request)' 'arquivo por argumento'
cob "padrões perigosos no executor varridos"

# ---- 6. permissões / escopo pedido ------------------------------------------
titulo "Permissões e escopo pedido"
PERM="$(grep -rniE '(allowed-tools|tools?:|permissions?:|scopes?:)' --include='*.md' --include='*.json' --include='*.yaml' "$ALVO" 2>/dev/null | grep -v node_modules | head -15)"
if [ -n "$PERM" ]; then echo "$PERM"; echo "-> pede mais do que a tarefa exige? (Bash/* para 'formatar texto' = agência excessiva)"; cob "escopo declarado extraído"
else echo "nenhum escopo declarado encontrado"; gap "escopo declarado (não encontrado)"; fi

# ---- 7. proveniência e cadeia ------------------------------------------------
titulo "Proveniência e cadeia"
PKG="$(find "$ALVO" -maxdepth 2 -name package.json -not -path '*/node_modules/*' 2>/dev/null | head -1)"
if [ -n "$PKG" ]; then
  grep -nE '"(name|version|author|repository|homepage|license)"' "$PKG" 2>/dev/null | head -8
  if grep -qE '"(pre|post)?install"\s*:' "$PKG" 2>/dev/null; then
    echo "!! script de instalação presente — roda na CONEXÃO, antes de qualquer ferramenta:"
    grep -nE '"(pre|post)?install"\s*:' "$PKG"
    gap "script de (pre/post)install — LER antes de instalar"
  fi
  grep -nE '"[^"]+"\s*:\s*"(\^|~|latest|\*|git\+|https?://)' "$PKG" >/dev/null 2>&1 \
    && echo "-> dependências por tag móvel/latest/url — risco de rug pull"
  cob "proveniência via package.json"
else
  echo "sem package.json — proveniência limitada"
  gap "proveniência (sem package.json)"
fi
grep -rniE 'npx.*(-y|latest)' --include='*.json' "$ALVO" 2>/dev/null | grep -v node_modules \
  && echo "-> config usa 'npx -y' / latest: baixa e executa sem pin a cada início"

# ---- 8. segredos e dependências ---------------------------------------------
titulo "Segredos e dependências"
if have gitleaks; then
  if gitleaks git --help >/dev/null 2>&1; then gitleaks git "$ALVO" --redact --no-banner 2>/dev/null | tail -5
  else gitleaks detect --source "$ALVO" --redact 2>/dev/null | tail -5; fi
  cob "gitleaks"
else echo "gitleaks ausente — brew install gitleaks"; gap "gitleaks ausente"; fi
if have osv-scanner; then osv-scanner scan source -r "$ALVO" 2>/dev/null | tail -15; cob "osv-scanner"
else echo "osv-scanner ausente — brew install osv-scanner"; gap "osv-scanner ausente (superfície das deps)"; fi

# ---- mapa de cobertura -------------------------------------------------------
titulo "MAPA DE COBERTURA (Fase 0)"
printf 'COBERTO:%b\n' "$COB"
printf 'NÃO COBERTO:%b\n' "${GAP:-\n  (nada — tudo coberto)}"
echo
echo "Próximo: Fase 1 — ler as descrições e o código dos executores, camada por camada."
