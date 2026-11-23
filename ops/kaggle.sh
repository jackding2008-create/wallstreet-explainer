#!/usr/bin/env bash
# Codespaces 侧的总调度：打包 → 推数据集 → 跑 Kaggle → 等 → 取回 → 落进片子目录。
#   bash ops/kaggle.sh init
#   bash ops/kaggle.sh models                 # 一次性：建 ws-models（ISNet 模型）
#   bash ops/kaggle.sh all   <片子目录>        # 一条龙
#   bash ops/kaggle.sh pack  <片子目录> [--w 1280] [--from 12] [--to 160]
#   bash ops/kaggle.sh push | run | status | wait | pull | apply <片子目录>
set -uo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD="$ROOT/build"
JOB="$BUILD/job"
OUT="$BUILD/out"
KSLUG="ws-worker"
KREF=""

log() { echo "== $* =="; }
die() { echo "错误：$*" >&2; exit 1; }

load_user() {
  if [ -z "${KAGGLE_USERNAME:-}" ] && [ -f "$HOME/.kaggle/kaggle.json" ]; then
    KAGGLE_USERNAME="$(python3 -c "import json,os;print(json.load(open(os.path.expanduser('~/.kaggle/kaggle.json')))['username'])")"
  fi
  [ -n "${KAGGLE_USERNAME:-}" ] || die "没有 KAGGLE_USERNAME。export 它，或在 ~/.kaggle/kaggle.json 里配好。"
  export KAGGLE_USERNAME
  KREF="$KAGGLE_USERNAME/$KSLUG"
}

write_creds() {
  if [ -n "${KAGGLE_KEY:-}" ]; then
    mkdir -p "$HOME/.kaggle"
    python3 - "$KAGGLE_USERNAME" "$KAGGLE_KEY" <<'PY'
import json, os, sys
p = os.path.expanduser("~/.kaggle/kaggle.json")
json.dump({"username": sys.argv[1], "key": sys.argv[2]}, open(p, "w"))
os.chmod(p, 0o600)
PY
  fi
}

cmd_init() {
  command -v kaggle >/dev/null || pip install -q kaggle
  load_user
  write_creds
  log "Kaggle 用户：$KAGGLE_USERNAME"
  command -v ffmpeg >/dev/null || die "没有 ffmpeg"
  command -v node >/dev/null || die "没有 node"
  node -e "require.resolve('playwright')" 2>/dev/null || echo "提示：还没 npm install / playwright install"
  echo "kaggle: $(kaggle --version 2>&1 | head -1)"
  echo "下一步：bash ops/kaggle.sh models"
}

cmd_models() {
  load_user; write_creds
  local ds="$BUILD/models-ds"
  mkdir -p "$ds"
  local onnx="$ds/isnet-general-use.onnx"
  if [ ! -s "$onnx" ]; then
    log "下载 ISNet（约 178MB，只下一次）"
    curl -fL --retry 3 -o "$onnx.part" \
      "https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx" \
      || die "ISNet 下载失败"
    mv "$onnx.part" "$onnx"
  fi
  cat > "$ds/dataset-metadata.json" <<JSON
{"title":"ws-models","id":"$KAGGLE_USERNAME/ws-models","licenses":[{"name":"other"}]}
JSON
  # whisper small 也放进模型数据集，Kaggle 每次跑就不用再下 500MB
  local wh="$ds/fw-small"
  if [ ! -s "$wh/model.bin" ]; then
    log "下载 faster-whisper-small（约 500MB）"
    python3 -c "import huggingface_hub" 2>/dev/null || pip install -q huggingface_hub
    python3 - "$wh" <<'PY'
import os, sys
from huggingface_hub import snapshot_download
d = sys.argv[1]
snapshot_download("Systran/faster-whisper-small", local_dir=d)
print("ok", d)
PY
  fi
  upsert_dataset "$ds" "models $(date -u +%FT%TZ)" "ws-models"
}

upsert_dataset() { # dir message slug
  local dir="$1" msg="$2" slug="$3"
  if kaggle datasets list -m 2>/dev/null | grep -q "$KAGGLE_USERNAME/$slug"; then
    kaggle datasets version -p "$dir" -m "$msg" --dir-mode zip
  else
    kaggle datasets create -p "$dir" --dir-mode zip
  fi
}

cmd_pack() {
  load_user
  [ $# -ge 1 ] || die "用法：bash ops/kaggle.sh pack <片子目录> [--w 1280] [--from 12] [--to 160]"
  node "$ROOT/ops/pack_job.mjs" "$@" --out "$JOB"
}

cmd_push() {
  load_user; write_creds
  [ -f "$JOB/job.json" ] || die "先 pack"
  # 用户名的占位符在 pack 时可能还没 export，这里补一刀
  python3 - "$JOB/dataset-metadata.json" "$KAGGLE_USERNAME" <<'PY'
import json, sys
p, u = sys.argv[1], sys.argv[2]
d = json.load(open(p)); d["id"] = f"{u}/ws-handoff"; json.dump(d, open(p, "w"), indent=1)
PY
  upsert_dataset "$JOB" "job $(date -u +%FT%TZ)" "ws-handoff"
}

cmd_run() {
  load_user; write_creds
  mkdir -p "$BUILD/kaggle"
  cp "$ROOT/ops/worker.py" "$BUILD/kaggle/worker.py"
  sed "s/__USER__/$KAGGLE_USERNAME/g" "$ROOT/ops/kernel-metadata.template.json" > "$BUILD/kaggle/kernel-metadata.json"
  local i
  for i in 1 2 3; do
    kaggle kernels push -p "$BUILD/kaggle" && return 0
    echo "push 失败；数据集可能还在处理，30 秒后重试（$i/3）" >&2
    sleep 30
  done
  return 1
}

cmd_status() { load_user; kaggle kernels status "$KREF"; }

cmd_wait() {
  load_user
  local i s
  for i in $(seq 1 240); do   # 4 小时，60 秒一次
    s="$(kaggle kernels status "$KREF" 2>&1 | tr '[:upper:]' '[:lower:]')"
    echo "[$(date +%H:%M:%S)] $s"
    case "$s" in
      *complete*) return 0 ;;
      *error*|*cancel*) return 1 ;;
    esac
    sleep 60
  done
  echo "等待超时" >&2; return 1
}

cmd_pull() {
  load_user; write_creds
  rm -rf "$OUT"; mkdir -p "$OUT"
  kaggle kernels output "$KREF" -p "$OUT" || echo "（取回失败；如果 kernel 还在跑就再等等）"
  if [ -f "$OUT/result.zip" ]; then
    unzip -o "$OUT/result.zip" -d "$OUT" >/dev/null && echo "解包 result.zip"
  fi
  [ -f "$OUT/meta.json" ] && cat "$OUT/meta.json"
}

cmd_apply() {
  local film="${1:-}"
  [ -n "$film" ] || die "用法：bash ops/kaggle.sh apply <片子目录>"
  [ -d "$film" ] || die "没有这个目录：$film"
  mkdir -p "$film/assets/cut" "$film/out"
  if [ -d "$OUT/cut" ]; then
    cp -r "$OUT/cut/." "$film/assets/cut/"
    echo "抠像已写入 $film/assets/cut/"
  fi
  if [ -f "$OUT/timeline.json" ]; then
    cp "$OUT/timeline.json" "$film/timeline.json"
    # Kaggle 上的 host 路径在 Codespaces 不存在，改回片子里的相对路径
    local hostrel="assets/host.mp4"
    [ -f "$film/assets/host.mp4" ] || hostrel="assets/host_raw.mp4"
    [ -f "$film/$hostrel" ] || hostrel=""
    if [ -n "$hostrel" ]; then
      node -e 'const fs=require("fs");const p=process.argv[1];const t=JSON.parse(fs.readFileSync(p,"utf8"));if(t.host)t.host.src=process.argv[2];fs.writeFileSync(p,JSON.stringify(t,null,1))' "$film/timeline.json" "$hostrel"
      echo "timeline.json 的 host.src → $hostrel"
    fi
    echo "时间线已写入 $film/timeline.json"
  fi
  [ -f "$OUT/meta.json" ] && cp "$OUT/meta.json" "$film/out/kaggle_meta.json"
  echo "完成。回到片子目录跑：node \"$ROOT/scripts/render.mjs\" --dir \"$film\" --check"
}

cmd_all() {
  local film="${1:-}"; shift || true
  [ -n "$film" ] || die "用法：bash ops/kaggle.sh all <片子目录>"
  cmd_pack "$film" "$@" || return 1
  cmd_push || return 1
  cmd_run || return 1
  local ok=0
  cmd_wait || ok=1
  cmd_pull
  cmd_apply "$film"
  return $ok
}

usage() {
  sed -n '2,12p' "$0"
}

cmd="${1:-}"; shift || true
case "$cmd" in
  init) cmd_init ;;
  models) cmd_models ;;
  pack) cmd_pack "$@" ;;
  push) cmd_push ;;
  run) cmd_run ;;
  status) cmd_status ;;
  wait) cmd_wait ;;
  pull) cmd_pull ;;
  apply) cmd_apply "$@" ;;
  all) cmd_all "$@" ;;
  *) usage ;;
esac
