#!/usr/bin/env bash
# 拉齐 kit/kit.css 要的字体。已存在且大于 100KB 就跳过。
#   bash ops/fetch_fonts.sh
#   bash ops/fetch_fonts.sh --check     # 只检查，不下载
set -uo pipefail
cd "$(dirname "$0")/.."
mkdir -p fonts

need=(
  BebasNeue-Regular.ttf
  AlimamaShuHeiTi-Bold.ttf
  MiSans-Regular.ttf
  MiSans-Medium.ttf
  MiSans-Semibold.ttf
  MiSans-Bold.ttf
  Montserrat-VF.ttf
  Montserrat-Italic-VF.ttf
)

check() {
  local miss=0
  for f in "${need[@]}"; do
    if [ -s "fonts/$f" ] && [ "$(stat -c%s "fonts/$f" 2>/dev/null || echo 0)" -gt 100000 ]; then
      echo "  ok   fonts/$f"
    else
      # kit.css 对 Medium/Semibold 同时接受 .otf
      local alt="${f%.ttf}.otf"
      if [ -s "fonts/$alt" ]; then
        echo "  ok   fonts/$alt"
      else
        echo "  MISS fonts/$f"; miss=$((miss+1))
      fi
    fi
  done
  [ "$miss" -eq 0 ] && echo "字体齐了。" || echo "缺 $miss 个。缺的会退到系统字体，样子不对。"
  return 0
}

if [ "${1:-}" = "--check" ]; then check; exit 0; fi

get() { # url dest
  local url="$1" dst="$2"
  if [ -s "$dst" ] && [ "$(stat -c%s "$dst")" -gt 100000 ]; then echo "skip $dst"; return 0; fi
  if curl -fL --retry 3 --connect-timeout 20 -o "$dst.part" "$url" && [ -s "$dst.part" ]; then
    mv "$dst.part" "$dst"; echo "ok   $dst"
  else
    rm -f "$dst.part"; echo "FAIL $dst"; return 1
  fi
}

echo "== Google Fonts =="
GF=https://raw.githubusercontent.com/google/fonts/main/ofl
get "$GF/bebasneue/BebasNeue-Regular.ttf" fonts/BebasNeue-Regular.ttf
get "$GF/montserrat/Montserrat%5Bwght%5D.ttf" fonts/Montserrat-VF.ttf
get "$GF/montserrat/Montserrat-Italic%5Bwght%5D.ttf" fonts/Montserrat-Italic-VF.ttf

echo "== 阿里妈妈数黑体（Shu） =="
get "https://raw.githubusercontent.com/ShuShuHong/FreeFronts/main/fonts/38_%E9%98%BF%E9%87%8C%E5%A6%88%E5%A6%88%E6%95%B0%E9%BB%91%E4%BD%93.ttf" fonts/AlimamaShuHeiTi-Bold.ttf

echo "== MiSans（小米官方 zip，约 220MB） =="
if [ ! -s fonts/MiSans-Regular.ttf ] || [ ! -s fonts/MiSans-Bold.ttf ]; then
  tmp="$(mktemp -d)"
  if curl -fL --retry 3 --connect-timeout 20 -o "$tmp/MiSans.zip" https://hyperos.mi.com/font-download/MiSans.zip; then
    unzip -o -j "$tmp/MiSans.zip" \
      '*MiSans-Regular.ttf' '*MiSans-Medium.ttf' '*MiSans-Semibold.ttf' '*MiSans-Bold.ttf' \
      '*MiSans-Medium.otf' '*MiSans-Semibold.otf' \
      -d fonts >/dev/null 2>&1 || true
    # 有些版本的 zip 是根目录文件名，再试一次不带路径
    unzip -o -j "$tmp/MiSans.zip" 'MiSans-Regular.ttf' 'MiSans-Medium.ttf' 'MiSans-Semibold.ttf' 'MiSans-Bold.ttf' -d fonts >/dev/null 2>&1 || true
  else
    echo "FAIL MiSans.zip（官网下载失败）。手动下载后把 MiSans-*.ttf 放进 fonts/。"
  fi
  rm -rf "$tmp"
else
  echo "skip MiSans"
fi

echo
check
echo
echo "阿里妈妈数黑体若缺失，去 https://www.alibabafonts.com/#/font 下载，"
echo "把 AlimamaShuHeiTi-Bold.ttf 放进 fonts/ 即可。"
