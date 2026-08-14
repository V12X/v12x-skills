#!/usr/bin/env bash
#
# v12x-scan · Fase 0 — ferramentas determinísticas
# -----------------------------------------------------------------------------
# Roda TODA a fase determinística de uma vez, degrada com elegância quando falta
# ferramenta (cada ausência já vira "NÃO COBERTO") e imprime o mapa de cobertura
# pronto no fim — que é exatamente o que o relatório final exige.
#
# É somente leitura no repositório alvo. Escreve apenas em $OUT e num /tmp próprio.
#
# Uso:
#   bash fase0.sh [dir-alvo]          # padrão: diretório atual
#   OUT=/caminho bash fase0.sh .      # muda onde os relatórios são salvos
#
# Compatível com o bash 3.2 do macOS. NÃO usa `set -e` de propósito: grep sem
# correspondência retorna 1 e abortaria a varredura no primeiro "nada encontrado".

set -u

ALVO="${1:-.}"
OUT="${OUT:-$ALVO/.security-reports/fase0}"
TMP="$(mktemp -d 2>/dev/null || echo "/tmp/v12x-fase0.$$")"
mkdir -p "$OUT" "$TMP" 2>/dev/null

# ---- infraestrutura de cobertura --------------------------------------------
COB=""   # o que ESTA execução conseguiu cobrir
GAP=""   # o que ficou de fora, e por quê
cob(){ COB="$COB\n  $1"; }
gap(){ GAP="$GAP\n  $1"; }
have(){ command -v "$1" >/dev/null 2>&1; }
titulo(){ printf '\n== %s ==\n' "$1"; }
# procura um arquivo (nome ou glob) até 4 níveis, ignorando vendor
detect(){ find "$ALVO" -maxdepth 4 -name "$1" \
  -not -path '*/node_modules/*' -not -path '*/vendor/*' -not -path '*/.git/*' \
  2>/dev/null | head -1; }
conta_json(){ # conta achados num relatório JSON do gitleaks
  [ -s "$1" ] || { echo 0; return; }
  if have jq; then jq 'length' "$1" 2>/dev/null || echo '?'
  else grep -o '"RuleID"' "$1" 2>/dev/null | wc -l | tr -d ' '; fi
}

# ---- âncora ------------------------------------------------------------------
titulo "Âncora"
COMMIT="$(git -C "$ALVO" rev-parse HEAD 2>/dev/null || echo 'sem git')"
echo "commit:    $COMMIT"
echo "data:      $(date '+%Y-%m-%d %H:%M')"
echo "alvo:      $ALVO"
echo "gitleaks:  $(gitleaks version 2>/dev/null || echo AUSENTE)"
echo "relatório: $OUT"

# ---- segredos: histórico do git ---------------------------------------------
titulo "Segredos — histórico do git"
if have gitleaks && [ "$COMMIT" != "sem git" ]; then
  # gitleaks >= 8.19 renomeou `detect` para `git`; detectar a forma disponível
  # (não dá para inferir pelo código de saída: `git`/`detect` retornam !=0 quando
  #  ACHAM segredo, não quando o subcomando é inválido)
  if gitleaks git --help >/dev/null 2>&1; then
    gitleaks git "$ALVO" --redact --report-format json --report-path "$OUT/gl-git.json" >/dev/null 2>&1 || true
  else
    gitleaks detect --source "$ALVO" --redact --report-format json --report-path "$OUT/gl-git.json" >/dev/null 2>&1 || true
  fi
  N="$(conta_json "$OUT/gl-git.json")"
  echo "achados no histórico: $N   ($OUT/gl-git.json)"
  cob "histórico git via gitleaks ($N achado(s))"
elif ! have gitleaks; then
  echo "gitleaks AUSENTE — brew install gitleaks"
  gap "segredos no histórico (gitleaks ausente)"
else
  echo "projeto sem git — varredura de histórico não se aplica"
  gap "histórico git (projeto sem git)"
fi

# ---- segredos: árvore de trabalho (não rastreados + ignorados) ---------------
titulo "Segredos — árvore de trabalho (não rastreados + ignorados)"
if have gitleaks && [ "$COMMIT" != "sem git" ]; then
  ALVOG="$TMP/gl-alvo"; mkdir -p "$ALVOG"
  { git -C "$ALVO" ls-files --others --exclude-standard;
    git -C "$ALVO" ls-files --others --ignored --exclude-standard; } \
    | grep -vE '^(node_modules|\.next|\.build|build|dist|Pods|\.vercel|DerivedData|vendor|target|__pycache__|\.venv)/' \
    | grep -vE '\.(png|jpg|jpeg|heic|webp|ico|woff2?|ttf|map)$' \
    | while read -r f; do
        [ -f "$ALVO/$f" ] && mkdir -p "$ALVOG/$(dirname "$f")" && cp "$ALVO/$f" "$ALVOG/$f" 2>/dev/null
      done
  gitleaks dir "$ALVOG" --redact --report-format json --report-path "$OUT/gl-tree.json" >/dev/null 2>&1 || true
  N="$(conta_json "$OUT/gl-tree.json")"
  echo "achados na árvore (ignorados/não rastreados): $N   ($OUT/gl-tree.json)"
  cob "árvore de trabalho com ignorados ($N achado(s))"
  rm -rf "$ALVOG"
else
  echo "gitleaks ausente ou projeto sem git — não coberto"
  gap "árvore de trabalho (gitleaks ausente ou sem git)"
fi

# ---- segredos VIVOS: trufflehog (verificação ativa) --------------------------
titulo "Segredos vivos — trufflehog (verificação ativa)"
if have trufflehog && [ "$COMMIT" != "sem git" ]; then
  trufflehog git "file://$ALVO" --only-verified --no-update 2>/dev/null | tee "$OUT/trufflehog.txt"
  echo "(vazio acima = nenhuma credencial VIVA confirmada — exposta e viva > exposta e revogada)"
  cob "verificação de credencial viva (trufflehog)"
else
  echo "trufflehog ausente — opcional: brew install trufflehog"
  gap "verificação de credencial viva (trufflehog ausente)"
fi

# ---- chaves e certificados soltos -------------------------------------------
titulo "Chaves e certificados soltos"
find "$ALVO" -type f \
  \( -name '*.p8' -o -name '*.p12' -o -name '*.pem' -o -name '*.key' \
     -o -name '*.keystore' -o -name '*.jks' -o -name '*.mobileprovision' \) \
  -not -path '*/node_modules/*' -not -path '*/.build/*' -not -path '*/vendor/*' \
  2>/dev/null | tee "$OUT/chaves-soltas.txt"
[ -s "$OUT/chaves-soltas.txt" ] && echo "^ revisar cada um" || echo "nenhum arquivo de chave solto"
cob "arquivos de chave soltos (find)"

# ---- .env versionado vs ignorado --------------------------------------------
titulo ".env versionado/ignorado"
find "$ALVO" -name '.env*' -not -path '*/node_modules/*' 2>/dev/null | while read -r f; do
  rel="${f#$ALVO/}"
  if git -C "$ALVO" check-ignore -q "$rel" 2>/dev/null; then echo "ok (ignorado): $f"
  else echo "EXPOSTO (rastreável pelo git): $f"; fi
done | tee "$OUT/env.txt"
[ -s "$OUT/env.txt" ] || echo "nenhum arquivo .env"
cob ".env exposto vs ignorado"

# ---- submódulos --------------------------------------------------------------
titulo "Submódulos"
git -C "$ALVO" submodule status 2>/dev/null | tee "$OUT/submodulos.txt"
if [ -s "$OUT/submodulos.txt" ]; then
  echo "^ cada submódulo tem histórico próprio — auditar cada um"
  cob "submódulos enumerados"
else
  echo "nenhum submódulo"
fi

# ---- ecossistemas e linguagem de backend ------------------------------------
titulo "Ecossistemas e linguagem de backend"
BE=""
[ -n "$(detect package.json)" ]                                   && { echo "Node/TS  (package.json)";                 BE="$BE node"; }
[ -n "$(detect requirements.txt)$(detect pyproject.toml)$(detect manage.py)" ] && { echo "Python   (requirements/pyproject/manage.py)"; BE="$BE python"; }
[ -n "$(detect go.mod)" ]                                         && { echo "Go       (go.mod)";                        BE="$BE go"; }
[ -n "$(detect Gemfile)" ]                                        && { echo "Ruby     (Gemfile)";                       BE="$BE ruby"; }
[ -n "$(detect composer.json)" ]                                  && { echo "PHP      (composer.json)";                 BE="$BE php"; }
[ -n "$(detect pom.xml)$(detect build.gradle)$(detect build.gradle.kts)" ] && { echo "Java/Kt  (pom.xml/build.gradle)";        BE="$BE java"; }
[ -n "$(detect '*.swift')$(detect project.yml)" ]                 && { echo "Swift    (.swift/project.yml)";            BE="$BE swift"; }
echo "-> Fase 1 aplica os padrões da(s) linguagem(ns):${BE:- nenhuma detectada}"
echo "   backend != TS/JS -> references/linguagens-backend.md (senão o furo é silencioso)"
cob "detecção de linguagem de backend:${BE:- nenhuma}"

# ---- dependências e lockfiles -----------------------------------------------
titulo "Dependências e lockfiles"
for lf in package-lock.json pnpm-lock.yaml yarn.lock Package.resolved go.sum \
          Gemfile.lock composer.lock poetry.lock requirements.txt; do
  [ -n "$(detect "$lf")" ] && echo "lockfile presente: $lf"
done
if [ -n "$(detect package.json)" ] && [ -n "$(detect package-lock.json)" ] && have npm; then
  ( cd "$ALVO" && npm audit --audit-level=high 2>/dev/null | tail -n 20 ) | tee "$OUT/npm-audit.txt"
  cob "npm audit (>=high)"
elif [ -n "$(detect package.json)" ]; then
  echo "package.json sem package-lock.json ou npm ausente — audit não roda de forma reproduzível"
  gap "npm audit (sem lockfile ou npm ausente)"
fi
if have osv-scanner; then
  osv-scanner scan source -r "$ALVO" 2>/dev/null | tail -n 40 | tee "$OUT/osv.txt"
  cob "osv-scanner (multi-ecossistema)"
else
  echo "osv-scanner AUSENTE — brew install osv-scanner (cobre SwiftPM, Go, Ruby, etc.)"
  gap "osv-scanner ausente (ecossistemas fora do npm sem audit central)"
fi
if [ -n "$(detect package.json)" ]; then
  grep -nE '"(pre|post)?install"[[:space:]]*:' "$ALVO"/package.json 2>/dev/null | tee "$OUT/lifecycle.txt"
  [ -s "$OUT/lifecycle.txt" ] && echo "^ script de ciclo de vida (postinstall/preinstall) — vetor de cadeia, revisar"
fi

# ---- padrões estáticos: semgrep ---------------------------------------------
titulo "Padrões estáticos — semgrep"
if have semgrep; then
  semgrep --config=auto --severity=ERROR --quiet "$ALVO" 2>/dev/null | tee "$OUT/semgrep.txt"
  echo "(config=auto baixa regras da nuvem; offline use --config=p/ci)"
  cob "semgrep (config=auto, ERROR)"
else
  echo "semgrep AUSENTE — brew install semgrep. NÃO bloqueia: seguir para a Fase 1."
  gap "semgrep ausente (análise estática de padrão)"
fi

# ---- CI e infraestrutura -----------------------------------------------------
titulo "CI e infraestrutura"
INFRA=0
[ -d "$ALVO/.github/workflows" ] && { echo ".github/workflows/ presente"; INFRA=1; }
[ -n "$(detect Dockerfile)" ]    && { echo "Dockerfile presente"; INFRA=1; }
[ -n "$(detect docker-compose.yml)$(detect docker-compose.yaml)" ] && { echo "docker-compose presente"; INFRA=1; }
[ "$INFRA" = 1 ] && echo "-> carregar references/cadeia-e-ci.md"
if [ ! -d "$ALVO/.github/workflows" ]; then
  echo "NOTA: sem CI detectado — a ausência de CI é achado Média (nada roda sozinho; ver assets/security-ci.yml)"
  gap "sem CI (nenhuma verificação roda sozinha — achado Média)"
fi

# ---- mapa de cobertura -------------------------------------------------------
titulo "MAPA DE COBERTURA (Fase 0)"
printf 'COBERTO:%b\n' "$COB"
printf 'NÃO COBERTO:%b\n' "${GAP:-\n  (nada — todas as ferramentas presentes)}"
{
  echo "commit: $COMMIT"
  echo "data:   $(date '+%Y-%m-%d %H:%M')"
  printf 'COBERTO:%b\n' "$COB"
  printf 'NÃO COBERTO:%b\n' "${GAP:-\n  nenhum}"
} > "$OUT/cobertura.txt"

echo
echo "Relatórios (JSON/txt) em: $OUT"
echo "Próximo: Fase 1 — análise por categoria, usando as linguagens detectadas acima."
rm -rf "$TMP" 2>/dev/null
