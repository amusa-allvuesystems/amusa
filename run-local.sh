#!/usr/bin/env bash
# Local CLI setup — no Streamlit.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
pip install -q -r requirements-cli.txt

echo ""
echo "Examples:"
echo "  python amusa.py convert -i users.csv"
echo "  python amusa.py convert -g 12345678-1234-1234-1234-123456789abc"
echo "  az login && python amusa.py lookup -i users.csv"
echo ""

exec "$@"
