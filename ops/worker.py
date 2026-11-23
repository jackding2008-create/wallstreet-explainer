# -*- coding: utf-8 -*-
"""Kaggle GPU worker：只干两件事——逐帧抠人（matte.py + matte_clean.py）和口播逐字对齐（host_timeline.py）。
由 ops/pack_job.mjs 打包、ops/kaggle.sh push/run 推上来。
输入：/kaggle/input/ws-handoff（job.json、clips/、host.mp4、script.json、scripts/）
     /kaggle/input/ws-models（isnet-general-use.onnx）
输出：/kaggle/working/result.zip（cut/*、timeline.json、meta.json）
"""
import os, sys, json, glob, time, shutil, zipfile, subprocess, traceback

IN = "/kaggle/input/ws-handoff"
MODELS = "/kaggle/input/ws-models"
WORK = "/kaggle/working"
CODE = os.path.join(WORK, "code")
OUT = os.path.join(WORK, "out")

os.makedirs(CODE, exist_ok=True)
os.makedirs(OUT, exist_ok=True)


def log(*a):
    print(*a, flush=True)


def run(cmd, **kw):
    log("+", " ".join(map(str, cmd)))
    return subprocess.run(cmd, check=True, **kw)


def pip(*pkgs):
    try:
        run([sys.executable, "-m", "pip", "install", "-q", "--no-input", *pkgs])
    except Exception as e:
        log("pip 失败:", pkgs, e)


def main():
    t0 = time.time()
    errors = []
    log("=" * 60)
    log("ws-worker 启动")
    log("输入目录:", IN)
    if not os.path.exists(os.path.join(IN, "job.json")):
        log("找不到 job.json。当前 /kaggle/input：", os.listdir("/kaggle/input") if os.path.isdir("/kaggle/input") else "无")
        return 1

    # 1) 依赖。faster-whisper 会顺带装 CPU 版 onnxruntime，所以最后再装 GPU 版覆盖它。
    log("== 安装依赖 ==")
    pip("faster-whisper")
    pip("onnxruntime-gpu")
    try:
        import onnxruntime as ort
        prov = ort.get_available_providers()
        log("onnxruntime providers:", prov)
        if "CUDAExecutionProvider" not in prov:
            log("CUDA EP 不可用，改装 CPU 版 onnxruntime（会慢很多）")
            pip("onnxruntime")
    except Exception as e:
        log("onnxruntime 导入失败:", e)
        errors.append(f"onnxruntime: {e}")

    # 2) 脚本
    for f in ("matte.py", "matte_clean.py", "host_timeline.py"):
        src = os.path.join(IN, "scripts", f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(CODE, f))
        else:
            errors.append(f"缺脚本 {f}")

    # 3) 抠像模型
    def link_model():
        src = os.path.join(MODELS, "isnet-general-use.onnx")
        if not os.path.exists(src):
            cands = glob.glob(os.path.join(MODELS, "**", "isnet-general-use.onnx"), recursive=True)
            src = cands[0] if cands else None
        if not src:
            return None
        dst = os.path.expanduser("~/.rembg/models/isnet-general-use/isnet-general-use.onnx")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if not os.path.exists(dst):
            try:
                os.symlink(src, dst)
            except OSError:
                shutil.copy2(src, dst)
        return dst

    model = link_model()
    log("抠像模型:", model or "没找到（ws-models 数据集没挂上？）")
    if not model:
        errors.append("没有 isnet-general-use.onnx")

    job = json.load(open(os.path.join(IN, "job.json"), encoding="utf-8"))
    log("job:", json.dumps(job, ensure_ascii=False)[:800])

    # 4) 抠像
    for m in job.get("matte", []):
        name = m.get("name") or os.path.basename(m["src"])
        src = os.path.join(IN, m["src"])
        dst = os.path.join(OUT, m["dst"])
        os.makedirs(dst, exist_ok=True)
        cmd = [sys.executable, os.path.join(CODE, "matte.py"), src, dst,
               "--w", str(m.get("w") or job.get("w") or 1920),
               "--from", str(m.get("from") or 1),
               "--to", str(m.get("to") or 10 ** 9)]
        try:
            run(cmd)
            if job.get("clean", True) and os.path.exists(os.path.join(CODE, "matte_clean.py")):
                cc = [sys.executable, os.path.join(CODE, "matte_clean.py"), dst]
                if m.get("cut_left"): cc += ["--cut-left", str(m["cut_left"])]
                if m.get("cut_right"): cc += ["--cut-right", str(m["cut_right"])]
                run(cc)
            log(f"抠像完成 {name}: {len(glob.glob(os.path.join(dst, '*.png')))} 帧")
        except Exception as e:
            log(f"抠像失败 {name}: {e}")
            traceback.print_exc()
            errors.append(f"matte {name}: {e}")

    # 5) 口播 ASR
    asr = job.get("asr")
    if asr:
        try:
            from faster_whisper.utils import download_model
            wdir = os.path.join(WORK, "fw-small")
            if not os.path.exists(os.path.join(wdir, "model.bin")):
                log("下载 faster-whisper-small …")
                wdir = download_model("small", output_dir=wdir)
            env = os.environ.copy()
            env["WHISPER_DIR"] = wdir
            # ASR 强制 CPU：T4 上 cuDNN/ctranslate2 版本不匹配的概率不低，CPU int8 对 1–3 分钟口播够用。
            if not job.get("asr_gpu"):
                env["CUDA_VISIBLE_DEVICES"] = ""
            cmd = [sys.executable, os.path.join(CODE, "host_timeline.py"),
                   os.path.join(IN, asr["video"]), os.path.join(IN, "script.json"),
                   os.path.join(OUT, "timeline.json")]
            if asr.get("tail") is not None:
                cmd += ["--tail", str(asr["tail"])]
            run(cmd, env=env)
            log("ASR 完成")
        except Exception as e:
            log("ASR 失败:", e)
            traceback.print_exc()
            errors.append(f"asr: {e}")

    # 6) 打包 + 元信息
    meta = {
        "film": job.get("film"),
        "seconds": round(time.time() - t0, 1),
        "matte": [m.get("name") for m in job.get("matte", [])],
        "asr": bool(asr),
        "errors": errors,
        "cuda": None,
    }
    try:
        import onnxruntime as ort
        meta["cuda"] = "CUDAExecutionProvider" in ort.get_available_providers()
    except Exception:
        pass
    with open(os.path.join(OUT, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)
    with open(os.path.join(WORK, "meta.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=1)

    zpath = os.path.join(WORK, "result.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_STORED) as z:
        for root, _, files in os.walk(OUT):
            for f in files:
                p = os.path.join(root, f)
                z.write(p, os.path.relpath(p, OUT))
    log(f"result.zip: {os.path.getsize(zpath) / 1024 / 1024:.1f} MB")
    log("errors:", errors or "无")
    log("用时:", meta["seconds"], "秒")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:
        traceback.print_exc()
        # 仍然写一个 meta，方便 pull 下来说清楚为什么失败
        try:
            json.dump({"fatal": str(e)}, open(os.path.join(WORK, "meta.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        except Exception:
            pass
        sys.exit(1)
