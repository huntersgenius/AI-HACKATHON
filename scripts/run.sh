#!/usr/bin/env bash
# Hamroh — start the dev server.
# Usage:  ./scripts/run.sh [port]

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PORT="${1:-${PORT:-5000}}"

cd "$PROJECT_DIR"

say() { printf '\033[0;36m==>\033[0m %s\n' "$1"; }

if [ ! -x "$VENV_DIR/bin/python" ]; then
  printf '\033[0;31mXATO:\033[0m .venv topilmadi. Avval ishga tushiring:  ./scripts/setup.sh\n' >&2
  exit 1
fi

# Port band bo'lsa, aniq xabar bering — Flask'ning xatosi tushunarsizroq.
# `ss`/`lsof` har doim ham o'rnatilmagan, shuning uchun portni Python orqali
# tekshiramiz: bu venv bor joyda doim ishlaydi.
if ! "$VENV_DIR/bin/python" - "$PORT" <<'PY'
import socket, sys
sock = socket.socket()
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
try:
    sock.bind(("0.0.0.0", int(sys.argv[1])))
except OSError:
    sys.exit(1)
finally:
    sock.close()
PY
then
  printf '\033[0;31mXATO:\033[0m %s port band. Boshqa port bilan urinib ko'\''ring:\n' "$PORT" >&2
  printf '       ./scripts/run.sh 5001\n' >&2
  printf '\n       Yoki portni bo'\''shating:\n' >&2
  printf '       fuser -k %s/tcp        # yoki:  kill $(lsof -t -i:%s)\n' "$PORT" "$PORT" >&2
  exit 1
fi

say "Hamroh ishga tushmoqda — http://localhost:$PORT"
say "To'xtatish uchun: Ctrl+C"

# WSL2'da Windows brauzeri localhost orqali kirsin uchun 0.0.0.0 da tinglaymiz.
export HOST="${HOST:-0.0.0.0}"
export PORT
exec "$VENV_DIR/bin/python" app.py
