#!/data/data/com.termux/files/usr/bin/bash
# Levanta el panel y lo abre en el navegador. Funciona en Termux y dentro de proot-distro.
set -e
cd "$(dirname "$0")"
PUERTO="${PANEL_PORT:-8765}"
URL="http://localhost:$PUERTO"

if ! command -v python3 >/dev/null; then
  echo "Falta Python. En Termux: pkg install python"
  exit 1
fi

if curl -s -o /dev/null "$URL/api/estado" 2>/dev/null; then
  echo "El panel ya está corriendo: $URL"
else
  nohup python3 server.py >/dev/null 2>&1 &
  sleep 1
  echo "Panel en $URL  (para cerrarlo: pkill -f server.py)"
fi

# Abre el navegador de Android si se puede
ABRIR=/data/data/com.termux/files/usr/bin/termux-open-url
[ -x "$ABRIR" ] && "$ABRIR" "$URL" 2>/dev/null || true
