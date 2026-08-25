#!/usr/bin/env bash
#
# sync-skills.sh — instala/atualiza as skills da V12X em ~/.claude/skills/
# ---------------------------------------------------------------------------
# O caminho manual, para quem usa o Claude Code fora do terminal (web/desktop),
# onde /plugin não existe. Copia cada skill deste repo para o diretório de skills
# do usuário. Rode depois de melhorar uma skill — a cópia não se atualiza sozinha.
#
#   bash scripts/sync-skills.sh            # sincroniza
#   bash scripts/sync-skills.sh --dry-run  # mostra o que faria, sem copiar
#   CLAUDE_SKILLS=/outro/dir bash scripts/sync-skills.sh
#
# Depois de sincronizar, REINICIE a sessão do Claude Code (skills entram no boot).

set -u
REPO="$(cd "$(dirname "$0")/.." && pwd)"
DST="${CLAUDE_SKILLS:-$HOME/.claude/skills}"
DRY=0; [ "${1:-}" = "--dry-run" ] && DRY=1

ver(){ grep -m1 'version:' "$1/SKILL.md" 2>/dev/null | tr -d ' "' | sed 's/version://' || echo '?'; }

[ -d "$REPO/skills" ] || { echo "não achei $REPO/skills"; exit 1; }
mkdir -p "$DST"
echo "repo:    $REPO/skills"
echo "destino: $DST"
[ $DRY = 1 ] && echo "(dry-run — nada será copiado)"
echo

n=0
for sdir in "$REPO"/skills/*/; do
  s="$(basename "$sdir")"
  [ -f "$sdir/SKILL.md" ] || { echo "  pulado $s (sem SKILL.md)"; continue; }
  antes='—'; [ -f "$DST/$s/SKILL.md" ] && antes="$(ver "$DST/$s")"
  novo="$(ver "$sdir")"
  if [ $DRY = 1 ]; then
    echo "  $s: $antes -> $novo (copiaria)"
  else
    if command -v rsync >/dev/null 2>&1; then
      rsync -a --delete "$sdir" "$DST/$s/"
    else
      rm -rf "$DST/$s"; cp -R "$sdir" "$DST/$s"
    fi
    # scripts executáveis
    find "$DST/$s/scripts" -type f \( -name '*.sh' -o -name '*.py' \) -exec chmod +x {} \; 2>/dev/null
    echo "  $s: $antes -> $novo ✓"
  fi
  n=$((n+1))
done

echo
echo "$n skill(s) processada(s)."
if [ $DRY = 0 ]; then echo "Agora REINICIE a sessão do Claude Code para elas entrarem no índice."; fi
exit 0
