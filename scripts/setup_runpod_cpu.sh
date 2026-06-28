#!/usr/bin/env bash
set -euo pipefail

if [[ ! -f "parallel_search_oneshot.py" || ! -f "voneshot.py" ]]; then
  echo "error: run this script from the OneShotPrimalityProofs repo root" >&2
  exit 2
fi

if command -v sudo >/dev/null 2>&1; then
  SUDO=sudo
else
  SUDO=
fi

if command -v apt-get >/dev/null 2>&1; then
  $SUDO apt-get update
  $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y \
    build-essential \
    git \
    libpari-dev \
    pari-gp \
    pkg-config \
    python3-dev \
    python3-pip \
    python3-venv
else
  echo "error: this bootstrap script expects an apt-based Ubuntu/Debian image" >&2
  exit 2
fi

python3 -m pip install --user --upgrade pip wheel
python3 -m pip install --user --upgrade cypari2

python3 - <<'PY'
from cypari2 import Pari
pari = Pari()
pari("default(nbthreads,1)")
assert int(pari("2+2")) == 4
assert int(pari("ellcard(ellinit([0,3,0,1,0],101))")) == 96
print("cypari2/PARI ok")
PY

python3 -m py_compile voneshot.py search_oneshot.py parallel_search_oneshot.py
python3 voneshot.py --test
python3 parallel_search_oneshot.py --prime 101 \
  --workers 2 \
  --seed 1 \
  --batch-size 1 \
  --max-curves-per-worker 8 \
  --report-every 1 \
  --report-seconds 0

cat <<'EOF'

RunPod CPU setup complete.

Example search:
  mkdir -p search_runs
  python3 parallel_search_oneshot.py 45 \
    --workers "$(nproc)" \
    --seed 202606280601 \
    --batch-size 8 \
    --report-every 500 \
    --report-seconds 30 \
    --log-file search_runs/search-45-runpod-a.jsonl \
    --result-file search_runs/cert-45-runpod-a.txt
EOF
