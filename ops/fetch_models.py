#!/usr/bin/env python3
"""把 worker 要用的模型下到本地一个目录，之后作为 Kaggle 数据集传上去。

    python ops/fetch_models.py build/models-ds

产物：
    <dir>/isnet-general-use.onnx     抠像模型（约 178MB）
    <dir>/fw-small/                  faster-whisper small（约 500MB，ASR 对齐用）

两个都是幂等的：文件已在就跳过。
"""
import os
import shutil
import sys
import urllib.request

ISNET_URL = "https://github.com/danielgatis/rembg/releases/download/v0.0.0/isnet-general-use.onnx"
ISNET_BYTES = 178_648_008


def log(msg):
    print(f"== {msg} ==", flush=True)


def download(url, dst, expect=None):
    part = dst + ".part"
    log(f"下载 {os.path.basename(dst)}")
    req = urllib.request.Request(url, headers={"User-Agent": "wallstreet-explainer/1.0"})
    with urllib.request.urlopen(req) as r, open(part, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        done = 0
        while True:
            chunk = r.read(1 << 20)
            if not chunk:
                break
            f.write(chunk)
            done += len(chunk)
            if total:
                pct = done * 100 // total
                if pct % 10 == 0:
                    print(f"  {pct}%  {done / 1e6:.0f}/{total / 1e6:.0f} MB", flush=True)
    size = os.path.getsize(part)
    if expect and size != expect:
        os.remove(part)
        raise SystemExit(f"大小不对：{size} != {expect}，已删除半成品，请重试")
    shutil.move(part, dst)
    log(f"完成 {os.path.basename(dst)}  {size / 1e6:.1f} MB")


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "build/models-ds"
    os.makedirs(out, exist_ok=True)

    onnx = os.path.join(out, "isnet-general-use.onnx")
    have = os.path.getsize(onnx) if os.path.exists(onnx) else 0
    if have == ISNET_BYTES:
        log("ISNet 已在，跳过")
    else:
        if have:
            log("ISNet 大小不对，重下")
            os.remove(onnx)
        download(ISNET_URL, onnx, ISNET_BYTES)

    wh = os.path.join(out, "fw-small")
    if os.path.exists(os.path.join(wh, "model.bin")):
        log("fw-small 已在，跳过")
    else:
        try:
            from huggingface_hub import snapshot_download
        except ImportError:
            raise SystemExit("需要 huggingface_hub：pip install huggingface_hub")
        log("下载 faster-whisper-small（Systran/faster-whisper-small）")
        snapshot_download("Systran/faster-whisper-small", local_dir=wh)
        log("完成 fw-small")

    log("模型目录就绪：" + os.path.abspath(out))


if __name__ == "__main__":
    main()
