#!/usr/bin/env bash
# 薄壳：真正的实现在 ops/kaggle.py（Windows / Linux 通用，一套逻辑）。
#   bash ops/kaggle.sh init
#   bash ops/kaggle.sh models
#   bash ops/kaggle.sh all <片子目录>
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="$(command -v python3 || command -v python)"
exec "$PY" "$ROOT/ops/kaggle.py" "$@"
