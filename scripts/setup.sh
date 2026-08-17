#!/usr/bin/env bash
# Hamroh — one-time setup for WSL / Ubuntu / macOS.
# Creates a virtualenv, installs dependencies and prepares .env.
# Safe to re-run: it never overwrites an existing .env.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="$PROJECT_DIR/.venv"
PYTHON_BIN="${PYTHON_BIN:-python3}"

cd "$PROJECT_DIR"

say()  { printf '\033[0;36m==>\033[0m %s\n' "$1"; }
warn() { printf '\033[0;33m!!\033[0m  %s\n' "$1"; }
die()  { printf '\033[0;31mXATO:\033[0m %s\n' "$1" >&2; exit 1; }

# --- 1. Python ------------------------------------------------------------
say "Python tekshirilmoqda…"
command -v "$PYTHON_BIN" >/dev/null 2>&1 || die \
  "python3 topilmadi. O'rnating:  sudo apt update && sudo apt install -y python3"

PY_VERSION="$("$PYTHON_BIN" -c 'import sys; print("%d.%d" % sys.version_info[:2])')"
"$PYTHON_BIN" - <<'PY' || die "Python 3.9+ kerak (hozir: $PY_VERSION)"
import sys
sys.exit(0 if sys.version_info >= (3, 9) else 1)
PY
say "Python $PY_VERSION topildi."

# --- 2. venv --------------------------------------------------------------
# Ubuntu/WSL'da python3-venv alohida paket bo'lib, ko'pincha o'rnatilmagan.
if ! "$PYTHON_BIN" -c 'import venv' >/dev/null 2>&1; then
  die "python3-venv yo'q. O'rnating:
       sudo apt update && sudo apt install -y python3-venv python3-pip"
fi

if [ -d "$VENV_DIR" ]; then
  say "Virtual muhit allaqachon bor: .venv"
else
  say "Virtual muhit yaratilmoqda: .venv"
  "$PYTHON_BIN" -m venv "$VENV_DIR" 2>/dev/null || die "venv yaratilmadi. O'rnating:
       sudo apt update && sudo apt install -y python3-venv"
fi

# --- 3. Kutubxonalar ------------------------------------------------------
say "Kutubxonalar o'rnatilmoqda (requirements.txt)…"
"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r requirements.txt
say "O'rnatildi: $("$VENV_DIR/bin/pip" list --format=freeze | wc -l) ta paket."

# --- 4. .env --------------------------------------------------------------
if [ -f .env ]; then
  say ".env allaqachon mavjud — tegilmadi."
else
  cp .env.example .env
  say ".env yaratildi (.env.example dan nusxa)."
  warn "ANTHROPIC_API_KEY bo'sh. Kalitsiz ham demo to'liq ishlaydi —"
  warn "AI o'rniga qoidalar analizatori ishlaydi (rule_analyzer)."
fi

# --- 5. Tekshiruv ---------------------------------------------------------
say "Smoke testlar ishga tushirilmoqda…"
if "$VENV_DIR/bin/python" -m pytest -q; then
  say "Testlar o'tdi."
else
  die "Testlar o'tmadi — yuqoridagi xatoni ko'ring."
fi

cat <<EOF

  Tayyor. Ishga tushirish:

      ./scripts/run.sh

  So'ng brauzerda oching:  http://localhost:5000

EOF
