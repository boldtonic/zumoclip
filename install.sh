#!/usr/bin/env bash
# Instala Zumoclip: OpenShorts, sus dependencias y los scripts de este repo.
#
#   bash install.sh           instala lo que falte; no toca lo que ya está
#   bash install.sh --check   solo comprueba, no instala nada
#
# Pensado para macOS con Homebrew. Nunca sobrescribe un .env existente.
set -uo pipefail

OPENSHORTS_HOME="${OPENSHORTS_HOME:-$HOME/openshorts}"
REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
FALTA=0

ok()    { printf '  ok      %s\n' "$1"; }
falta() { printf '  falta   %s\n' "$1"; FALTA=1; }

# ffmpeg con libass: el normal de Homebrew no puede quemar subtítulos.
ffmpeg_full() {
  local p
  for p in /opt/homebrew/opt/ffmpeg-full/bin/ffmpeg /usr/local/opt/ffmpeg-full/bin/ffmpeg; do
    [ -x "$p" ] || continue
    # Se guarda la salida antes de buscar: con pipefail, `| grep -q` corta la
    # tubería al primer acierto, ffmpeg recibe SIGPIPE y el conjunto "falla".
    local filtros
    filtros="$("$p" -hide_banner -filters 2>/dev/null)" || continue
    case "$filtros" in *" ass "*) echo "$p"; return 0 ;; esac
  done
  return 1
}

hay_clave() {
  [ -f "$OPENSHORTS_HOME/.env" ] && grep -qE '^GEMINI_API_KEY=.+' "$OPENSHORTS_HOME/.env"
}

comprobar() {
  echo "Comprobando..."
  if command -v brew       >/dev/null 2>&1; then ok "Homebrew";      else falta "Homebrew  (https://brew.sh)"; fi
  if command -v python3.11 >/dev/null 2>&1; then ok "Python 3.11";   else falta "Python 3.11"; fi
  if command -v ffmpeg     >/dev/null 2>&1; then ok "ffmpeg";        else falta "ffmpeg  (lo usa OpenShorts)"; fi
  if ffmpeg_full           >/dev/null;      then ok "ffmpeg-full con libass"; else falta "ffmpeg-full con libass  (para quemar subtítulos)"; fi
  if command -v deno       >/dev/null 2>&1; then ok "deno";          else falta "deno  (lo necesita yt-dlp para YouTube)"; fi
  if [ -f "$OPENSHORTS_HOME/main.py" ];     then ok "OpenShorts en $OPENSHORTS_HOME"; else falta "OpenShorts en $OPENSHORTS_HOME"; fi
  if [ -x "$OPENSHORTS_HOME/.venv/bin/python" ]; then ok "entorno de Python de OpenShorts"; else falta "entorno de Python de OpenShorts"; fi
  local s al_dia=1
  for s in "$REPO_DIR"/scripts/*.py; do
    cmp -s "$s" "$OPENSHORTS_HOME/$(basename "$s")" || al_dia=0
  done
  if [ "$al_dia" = 1 ]; then ok "scripts de Zumoclip al día"; else falta "scripts de Zumoclip copiados y al día"; fi
  if hay_clave; then ok "GEMINI_API_KEY en .env"; else falta "GEMINI_API_KEY en $OPENSHORTS_HOME/.env"; fi
}

instalar() {
  command -v brew >/dev/null 2>&1 || { echo "Instala Homebrew primero: https://brew.sh"; exit 1; }

  local pkgs=()
  command -v python3.11 >/dev/null 2>&1 || pkgs+=(python@3.11)
  command -v ffmpeg     >/dev/null 2>&1 || pkgs+=(ffmpeg)
  ffmpeg_full           >/dev/null      || pkgs+=(ffmpeg-full)
  command -v deno       >/dev/null 2>&1 || pkgs+=(deno)
  if [ ${#pkgs[@]} -gt 0 ]; then
    echo "brew install ${pkgs[*]}"
    brew install "${pkgs[@]}" || exit 1
  fi

  if [ ! -f "$OPENSHORTS_HOME/main.py" ]; then
    if [ -e "$OPENSHORTS_HOME" ]; then
      echo "$OPENSHORTS_HOME existe pero no es OpenShorts. Muévelo o fija OPENSHORTS_HOME."; exit 1
    fi
    git clone https://github.com/mutonby/openshorts.git "$OPENSHORTS_HOME" || exit 1
  fi

  if [ ! -x "$OPENSHORTS_HOME/.venv/bin/python" ]; then
    echo "Instalando las dependencias de OpenShorts (unos 2 GB, tarda un rato)..."
    python3.11 -m venv "$OPENSHORTS_HOME/.venv" || exit 1
    "$OPENSHORTS_HOME/.venv/bin/pip" install -q -r "$OPENSHORTS_HOME/requirements.txt" || exit 1
  fi

  cp "$REPO_DIR"/scripts/*.py "$OPENSHORTS_HOME/" || exit 1
  echo "Scripts de Zumoclip copiados a $OPENSHORTS_HOME"

  if [ ! -f "$OPENSHORTS_HOME/.env" ]; then
    if [ -f "$OPENSHORTS_HOME/.env.example" ]; then
      cp "$OPENSHORTS_HOME/.env.example" "$OPENSHORTS_HOME/.env"
    else
      echo "GEMINI_API_KEY=" > "$OPENSHORTS_HOME/.env"
    fi
    chmod 600 "$OPENSHORTS_HOME/.env"
    echo "Creado $OPENSHORTS_HOME/.env"
  fi
}

if [ "${1:-}" = "--check" ]; then
  comprobar
  if [ "$FALTA" = 0 ]; then echo "Todo listo."; else echo "Falta algo. Ejecuta:  bash install.sh"; fi
  exit "$FALTA"
fi

instalar
echo
comprobar
echo
if ! hay_clave; then
  echo "Último paso: pon tu clave de Gemini en $OPENSHORTS_HOME/.env"
  echo "  GEMINI_API_KEY=tu_clave     (gratis en https://aistudio.google.com/app/apikey)"
fi
exit "$FALTA"
