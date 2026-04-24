#!/bin/bash

# =============================================
# flight-alerts setup script
# =============================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[✓]${NC} $1"; }
info() { echo -e "${YELLOW}[→]${NC} $1"; }
warn() { echo -e "${RED}[!]${NC} $1"; }

echo "========================================"
echo "  flight-alerts setup"
echo "========================================"
echo "Project dir: $PROJECT_DIR"
echo ""

# -----------------------------------------------
# 1. Check Python 3.10+
# -----------------------------------------------
info "Checking Python version..."
if ! command -v python3 >/dev/null 2>&1; then
  warn "python3 not found. Install it first (e.g. 'sudo apt install python3 python3-venv')."
  exit 1
fi
PY_VERSION=$(python3 -c 'import sys; print("%d.%d" % sys.version_info[:2])')
log "Python $PY_VERSION detected"

# Ensure venv + ensurepip are available (Debian/Ubuntu ships them separately)
if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  warn "python3-venv / ensurepip is missing."
  if command -v apt-get >/dev/null 2>&1; then
    VENV_PKG="python${PY_VERSION}-venv"
    info "Installing $VENV_PKG via apt (requires sudo)..."
    if sudo apt-get update -y && sudo apt-get install -y "$VENV_PKG"; then
      log "$VENV_PKG installed"
    else
      warn "apt install failed. Try manually: sudo apt install $VENV_PKG"
      exit 1
    fi
  else
    warn "Install the venv module for your Python, then re-run this script."
    exit 1
  fi
fi

# -----------------------------------------------
# 2. Create virtualenv
# -----------------------------------------------
if [ ! -d "venv" ] || [ ! -x "venv/bin/python" ]; then
  if [ -d "venv" ]; then
    warn "Removing incomplete venv directory"
    rm -rf venv
  fi
  info "Creating virtualenv at ./venv..."
  python3 -m venv venv
  log "venv created"
else
  log "venv already exists, skipping"
fi

# shellcheck disable=SC1091
source venv/bin/activate
log "venv activated: $(which python)"

# -----------------------------------------------
# 3. Install dependencies
# -----------------------------------------------
info "Upgrading pip..."
pip install --quiet --upgrade pip
log "pip $(pip --version | awk '{print $2}')"

info "Installing requirements..."
pip install --quiet -r requirements.txt
log "Requirements installed"

# -----------------------------------------------
# 4. Bootstrap .env
# -----------------------------------------------
if [ ! -f ".env" ]; then
  info "Creating .env from .env.example..."
  cp .env.example .env
  warn "Edit .env and fill in:"
  warn "  - AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET (from developers.amadeus.com)"
  warn "  - TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID (from @BotFather)"
  warn "  - DATABASE_URL (from your Neon project dashboard)"
else
  log ".env already exists, not overwriting"
fi

# -----------------------------------------------
# 5. Apply schema (optional)
# -----------------------------------------------
echo ""
read -p "Apply schema.sql to DATABASE_URL now? (requires psql) [y/N] " APPLY_SCHEMA
if [[ "$APPLY_SCHEMA" =~ ^[Yy]$ ]]; then
  if ! command -v psql >/dev/null 2>&1; then
    warn "psql not found. Skipping — main.py will auto-apply schema on first run."
  else
    set -a; source .env; set +a
    if [ -z "${DATABASE_URL:-}" ]; then
      warn "DATABASE_URL not set in .env, skipping schema apply"
    else
      info "Applying schema..."
      psql "$DATABASE_URL" -f schema.sql
      log "Schema applied"
    fi
  fi
else
  info "Skipping — main.py will auto-apply schema on first run"
fi

# -----------------------------------------------
# Done
# -----------------------------------------------
echo ""
echo "========================================"
echo "  Setup complete"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Edit .env with your credentials"
echo "  2. Smoke test:    ./venv/bin/python src/main.py"
echo "  3. Add cron entry (runs 7am Tue–Thu only):"
echo ""
echo "       0 7 * * 2-4 $PROJECT_DIR/venv/bin/python $PROJECT_DIR/src/main.py >> $PROJECT_DIR/run.log 2>&1"
echo ""
echo "     Install via:  crontab -e"
echo ""
