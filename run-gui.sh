#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt

echo ""
echo "Starting Daily Attendance at http://localhost:8501"
echo "Press Ctrl+C to stop."
echo ""

exec streamlit run gui/app.py --server.address localhost --server.port 8501
