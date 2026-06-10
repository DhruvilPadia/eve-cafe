#!/usr/bin/env bash
# ─────────────────────────────────────────────────
#  Eve Café — Startup Script
#  Usage: ./start.sh [port]
# ─────────────────────────────────────────────────

set -e

PORT="${1:-5000}"
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DB="$DIR/eve_cafe.db"
LOG="$DIR/server.log"
PID_FILE="$DIR/server.pid"

GREEN='\033[0;32m'
GOLD='\033[0;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo -e "${GOLD}  ╔══════════════════════════════╗${NC}"
echo -e "${GOLD}  ║       🍃  Eve Café           ║${NC}"
echo -e "${GOLD}  ║   Full-Stack Ordering App    ║${NC}"
echo -e "${GOLD}  ╚══════════════════════════════╝${NC}"
echo ""

# ── Check Python ───────────────────────────────
if ! command -v python3 &>/dev/null; then
  echo -e "${RED}✗ Python 3 not found. Please install Python 3.8+${NC}"
  exit 1
fi
PYVER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${GREEN}✓${NC} Python $PYVER"

# ── Check Flask ────────────────────────────────
if ! python3 -c "import flask" &>/dev/null; then
  echo -e "${RED}✗ Flask not found. Install it:${NC}  pip install flask"
  exit 1
fi
FLASKVER=$(python3 -c "import flask; print(flask.__version__)")
echo -e "${GREEN}✓${NC} Flask $FLASKVER"

# ── Kill existing server on same port ─────────
if [ -f "$PID_FILE" ]; then
  OLD_PID=$(cat "$PID_FILE")
  if kill -0 "$OLD_PID" 2>/dev/null; then
    echo -e "${GREEN}↺${NC} Stopping old server (PID $OLD_PID)..."
    kill "$OLD_PID" 2>/dev/null || true
    sleep 1
  fi
  rm -f "$PID_FILE"
fi

# ── Start server ───────────────────────────────
cd "$DIR"
echo -e "${GREEN}✓${NC} Starting server on port $PORT..."
PORT=$PORT nohup python3 server.py > "$LOG" 2>&1 &
echo $! > "$PID_FILE"

# ── Wait for ready ─────────────────────────────
echo -n "  Waiting for server"
for i in {1..15}; do
  sleep 1
  echo -n "."
  if python3 -c "
import urllib.request
try:
    urllib.request.urlopen('http://localhost:$PORT/api/health', timeout=2)
    exit(0)
except:
    exit(1)
" 2>/dev/null; then
    echo ""
    break
  fi
  if [ $i -eq 15 ]; then
    echo ""
    echo -e "${RED}✗ Server failed to start. Check $LOG${NC}"
    exit 1
  fi
done

echo ""
echo -e "${GREEN}✓ Eve Café is running!${NC}"
echo ""
echo -e "  ${GOLD}Customer App:${NC}   http://localhost:$PORT/"
echo -e "  ${GOLD}Admin Login:${NC}    http://localhost:$PORT/ → tap 🔐 Staff"
echo -e "  ${GOLD}API Health:${NC}     http://localhost:$PORT/api/health"
echo ""
echo -e "  ${GOLD}Admin credentials:${NC}"
echo -e "    Login ID : AD.com"
echo -e "    Password : thisisbusiness"
echo ""
echo -e "  Logs: $LOG   |   DB: $DB"
echo -e "  Stop: kill \$(cat $PID_FILE)"
echo ""
