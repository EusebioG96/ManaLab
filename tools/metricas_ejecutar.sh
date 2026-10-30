#!/usr/bin/env bash
# Métricas semanales de ManaLab (ML-057). Pensado para una sesión en la nube nueva y sin contexto.
# Clona el repo, ejecuta tools/metricas_semanales.py con el histórico de la rama huérfana `metricas-datos`,
# sube SOLO historico.json a esa rama (nunca a main) e imprime el resumen en markdown.
# Variables opcionales: MANALAB_REPO_URL (por defecto GitHub), MANALAB_SIN_PUSH=1 (probar sin subir nada).
set -euo pipefail

REPO_URL="${MANALAB_REPO_URL:-https://github.com/EusebioG96/manalab.git}"
RAMA_DATOS="metricas-datos"
RAMA_HERRAMIENTAS="herramientas/ML-057-metricas"
HOY="$(date -u +%Y-%m-%d)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

[ "$RAMA_DATOS" != "main" ] || { echo "ERROR: la rama de datos no puede ser main" >&2; exit 1; }

git clone --quiet "$REPO_URL" "$TMP/repo"
cd "$TMP/repo"
git config user.name "${GIT_AUTHOR_NAME:-ManaLab métricas}"
git config user.email "${GIT_AUTHOR_EMAIL:-metricas@manalab.es}"

# 1) El script se toma de main; si aún no está publicado ahí, de la rama de herramientas (aviso a stderr).
ORIGEN="origin/main"
if ! git cat-file -e "$ORIGEN:tools/metricas_semanales.py" 2>/dev/null; then
  ORIGEN="origin/$RAMA_HERRAMIENTAS"
  git cat-file -e "$ORIGEN:tools/metricas_semanales.py" 2>/dev/null \
    || { echo "ERROR: tools/metricas_semanales.py no está ni en main ni en $RAMA_HERRAMIENTAS" >&2; exit 1; }
  echo "AVISO: metricas_semanales.py aún no está en main; usando $RAMA_HERRAMIENTAS" >&2
fi
mkdir -p "$TMP/herr/tools"
git show "$ORIGEN:tools/metricas_semanales.py" > "$TMP/herr/tools/metricas_semanales.py"
git show origin/main:sitemap.xml > "$TMP/herr/sitemap.xml" 2>/dev/null || true   # para listar las guías

# 2) Rama de datos: la existente o una huérfana nueva.
if git rev-parse --verify --quiet "origin/$RAMA_DATOS" >/dev/null; then
  git checkout --quiet -B "$RAMA_DATOS" "origin/$RAMA_DATOS"
else
  git checkout --quiet --orphan "$RAMA_DATOS"
  git rm -rf --quiet . >/dev/null 2>&1 || true
  find . -mindepth 1 -maxdepth 1 ! -name .git -exec rm -rf {} +
fi

# 3) Ejecutar (si falla, no se sube nada).
python3 "$TMP/herr/tools/metricas_semanales.py" --historico historico.json > "$TMP/resumen.md"

# 4) Commit de historico.json y push solo a metricas-datos.
git add historico.json
SUBIDO="sin cambios que subir"
if ! git diff --cached --quiet; then
  git commit --quiet -m "Métricas $HOY"
  if [ "${MANALAB_SIN_PUSH:-0}" = "1" ]; then
    SUBIDO="commit hecho, push omitido (MANALAB_SIN_PUSH=1)"
  elif git push --quiet origin "refs/heads/$RAMA_DATOS:refs/heads/$RAMA_DATOS"; then
    SUBIDO="historico.json subido a $RAMA_DATOS"
  else
    cat "$TMP/resumen.md"; echo; echo "ERROR: el push a $RAMA_DATOS falló; el histórico de hoy NO se guardó" >&2; exit 2
  fi
fi

cat "$TMP/resumen.md"
echo
echo "_Histórico: $SUBIDO._"
