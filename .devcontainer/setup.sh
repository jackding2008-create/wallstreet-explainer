#!/usr/bin/env bash
# Codespaces 一次性配置：ffmpeg、Python 依赖、Playwright、字体、容器内 Chromium 参数。
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== 1/5 apt：ffmpeg + 字体兜底 =="
sudo apt-get update -y
sudo apt-get install -y --no-install-recommends ffmpeg unzip fonts-noto-cjk

echo "== 2/5 Python 依赖 =="
python3 -m pip install --upgrade pip
pip install -r requirements.txt

echo "== 3/5 Node + Playwright Chromium =="
npm install
npx playwright install --with-deps chromium

echo "== 4/5 容器里的 Chromium 加 --no-sandbox =="
# Codespaces 的 Docker seccomp 默认不允许 Chromium 的用户命名空间沙箱。
# render.mjs 的 launch 参数是写死的，这里只补一个参数，不动其它逻辑。
if ! grep -q -- "--no-sandbox" scripts/render.mjs; then
  sed -i "s/args: \['--force-color-profile=srgb', '--disable-lcd-text'\]/args: ['--force-color-profile=srgb', '--disable-lcd-text', '--no-sandbox']/" scripts/render.mjs
  echo "已给 render.mjs 补 --no-sandbox"
else
  echo "render.mjs 已有 --no-sandbox"
fi

echo "== 5/5 字体 =="
bash ops/fetch_fonts.sh || true
bash ops/fetch_fonts.sh --check || true

echo
echo "完成。下一步："
echo "  export KAGGLE_USERNAME=... KAGGLE_KEY=..."
echo "  bash ops/kaggle.sh init"
echo "  bash ops/kaggle.sh models      # 只跑一次，建 ws-models 数据集"
