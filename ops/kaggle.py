#!/usr/bin/env python3
"""Codespaces / 本机通用的总调度：打包 → 推数据集 → 跑 Kaggle → 等 → 取回 → 落进片子目录。

    python ops/kaggle.py init
    python ops/kaggle.py models                       # 一次性：建 ws-models
    python ops/kaggle.py all    <片子目录>             # 一条龙
    python ops/kaggle.py pack   <片子目录> [--w 1280] [--from 12] [--to 160]
    python ops/kaggle.py push | run | status | wait | pull | apply <片子目录>

凭证（二选一）：
  * KAGGLE_USERNAME + KAGGLE_KEY   —— 传统 kaggle.json 那对
  * KAGGLE_API_TOKEN=KGAT_...      —— 新版 token，CLI 自己认
"""
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "build")
JOB = os.path.join(BUILD, "job")
OUT = os.path.join(BUILD, "out")
MODELS = os.path.join(BUILD, "models-ds")
SLUG = "ws-worker"

USER = ""


def log(msg):
    print(f"== {msg} ==", flush=True)


def die(msg):
    print(f"错误：{msg}", file=sys.stderr, flush=True)
    raise SystemExit(1)


def run(cmd, check=True, quiet=False, cwd=None):
    p = subprocess.run(
        cmd,
        cwd=cwd or ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    out = (p.stdout or "").strip()
    if p.returncode != 0 and check:
        print(out, file=sys.stderr)
        die(f"命令失败（{p.returncode}）：{' '.join(cmd[:3])} …")
    if not quiet and out:
        print(out, flush=True)
    return out


def kaggle_bin():
    forced = os.environ.get("KAGGLE_BIN")
    if forced:
        return forced.split()
    if importlib.util.find_spec("kaggle") is not None:
        return [sys.executable, "-m", "kaggle"]
    return ["kaggle"]


def kaggle(*args, check=True, quiet=False):
    return run(kaggle_bin() + [str(a) for a in args], check=check, quiet=quiet)


def ensure_cli():
    if importlib.util.find_spec("kaggle") is None and not shutil.which("kaggle"):
        log("安装 kaggle CLI")
        run([sys.executable, "-m", "pip", "install", "-q", "kaggle"])


def write_creds():
    key = os.environ.get("KAGGLE_KEY")
    user = os.environ.get("KAGGLE_USERNAME")
    if not (key and user):
        return
    d = os.path.join(os.path.expanduser("~"), ".kaggle")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "kaggle.json")
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"username": user, "key": key}, f)
    try:
        os.chmod(p, 0o600)
    except OSError:
        pass


def get_user():
    global USER
    if USER:
        return USER
    ensure_cli()
    write_creds()
    u = os.environ.get("KAGGLE_USERNAME")
    if not u:
        view = kaggle("config", "view", check=False, quiet=True)
        for line in view.splitlines():
            line = line.strip()
            if line.startswith("- username:"):
                u = line.split(":", 1)[1].strip()
                break
    if not u or u == "None":
        die("拿不到 Kaggle 用户名。export KAGGLE_USERNAME，或跑一次 kaggle login / 配 ~/.kaggle/kaggle.json。")
    USER = u
    return USER


def upsert_dataset(directory, message, slug):
    user = get_user()
    ref = f"{user}/{slug}"
    listing = kaggle("datasets", "list", "-m", "--page-size", "100", check=False, quiet=True)
    if ref in listing:
        log(f"更新数据集 {ref}")
        kaggle("datasets", "version", "-p", directory, "-m", message, "--dir-mode", "zip")
    else:
        log(f"新建数据集 {ref}")
        kaggle("datasets", "create", "-p", directory, "--dir-mode", "zip")


# ---------------------------------------------------------------- init / models


def cmd_init(argv):
    ensure_cli()
    user = get_user()
    log(f"Kaggle 用户：{user}")
    if not shutil.which("ffmpeg"):
        die("没有 ffmpeg")
    if not shutil.which("node"):
        die("没有 node")
    try:
        run(["node", "-e", "require.resolve('playwright')"], quiet=True)
    except SystemExit:
        print("提示：还没 npm install / playwright install chromium", flush=True)
    print(kaggle("--version", check=False, quiet=True))
    log("下一步：python ops/kaggle.py models")


def cmd_models(argv):
    get_user()
    os.makedirs(MODELS, exist_ok=True)
    run([sys.executable, os.path.join(ROOT, "ops", "fetch_models.py"), MODELS])
    meta = {"title": "ws-models", "id": f"{get_user()}/ws-models", "licenses": [{"name": "other"}]}
    with open(os.path.join(MODELS, "dataset-metadata.json"), "w", encoding="utf-8") as f:
        json.dump(meta, f)
    upsert_dataset(MODELS, "models " + time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "ws-models")


# --------------------------------------------------------------------- job flow


def cmd_pack(argv):
    if not argv:
        die("用法：python ops/kaggle.py pack <片子目录> [--w 1280] [--from 12] [--to 160]")
    run(["node", os.path.join(ROOT, "ops", "pack_job.mjs"), *argv, "--out", JOB])


def cmd_push(argv):
    user = get_user()
    p = os.path.join(JOB, "dataset-metadata.json")
    if not os.path.exists(os.path.join(JOB, "job.json")):
        die("先 pack")
    with open(p, encoding="utf-8") as f:
        d = json.load(f)
    d["id"] = f"{user}/ws-handoff"
    with open(p, "w", encoding="utf-8") as f:
        json.dump(d, f)
    upsert_dataset(JOB, "job " + time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "ws-handoff")


def cmd_run(argv):
    user = get_user()
    d = os.path.join(BUILD, "kaggle")
    os.makedirs(d, exist_ok=True)
    shutil.copy(os.path.join(ROOT, "ops", "worker.py"), os.path.join(d, "worker.py"))
    with open(os.path.join(ROOT, "ops", "kernel-metadata.template.json"), encoding="utf-8") as f:
        meta = f.read().replace("__USER__", user)
    with open(os.path.join(d, "kernel-metadata.json"), "w", encoding="utf-8") as f:
        f.write(meta)
    for i in range(1, 4):
        if subprocess.run(kaggle_bin() + ["kernels", "push", "-p", d], cwd=ROOT).returncode == 0:
            return
        print(f"push 失败；数据集可能还在处理，30 秒后重试（{i}/3）", file=sys.stderr, flush=True)
        time.sleep(30)
    die("kernel push 三次都失败")


def cmd_status(argv):
    kaggle("kernels", "status", f"{get_user()}/{SLUG}")


def cmd_wait(argv):
    ref = f"{get_user()}/{SLUG}"
    for _ in range(240):  # 4 小时，60 秒一次
        s = kaggle("kernels", "status", ref, check=False, quiet=True).lower()
        print(time.strftime("[%H:%M:%S] ") + s.replace("\n", " "), flush=True)
        if "complete" in s:
            return
        if "error" in s or "cancel" in s:
            die("kernel 失败，看上面的日志或 kaggle 网页版 Log")
        time.sleep(60)
    die("等待超时")


def cmd_pull(argv):
    if os.path.isdir(OUT):
        shutil.rmtree(OUT)
    os.makedirs(OUT)
    kaggle("kernels", "output", f"{get_user()}/{SLUG}", "-p", OUT, check=False)
    z = os.path.join(OUT, "result.zip")
    if os.path.exists(z):
        log("解包 result.zip")
        with zipfile.ZipFile(z) as zf:
            zf.extractall(OUT)
    meta = os.path.join(OUT, "meta.json")
    if os.path.exists(meta):
        print(open(meta, encoding="utf-8").read(), flush=True)


def cmd_apply(argv):
    film = argv[0] if argv else ""
    if not film:
        die("用法：python ops/kaggle.py apply <片子目录>")
    if not os.path.isdir(film):
        die(f"没有这个目录：{film}")
    os.makedirs(os.path.join(film, "assets", "cut"), exist_ok=True)
    os.makedirs(os.path.join(film, "out"), exist_ok=True)

    cut = os.path.join(OUT, "cut")
    if os.path.isdir(cut):
        shutil.copytree(cut, os.path.join(film, "assets", "cut"), dirs_exist_ok=True)
        log(f"抠像已写入 {film}/assets/cut/")

    tl = os.path.join(OUT, "timeline.json")
    if os.path.exists(tl):
        shutil.copy(tl, os.path.join(film, "timeline.json"))
        hostrel = ""
        for cand in ("assets/host.mp4", "assets/host_raw.mp4"):
            if os.path.exists(os.path.join(film, cand.replace("/", os.sep))):
                hostrel = cand
                break
        if hostrel:
            with open(os.path.join(film, "timeline.json"), encoding="utf-8") as f:
                t = json.load(f)
            if t.get("host"):
                t["host"]["src"] = hostrel
            with open(os.path.join(film, "timeline.json"), "w", encoding="utf-8") as f:
                json.dump(t, f, ensure_ascii=False, indent=1)
            log(f"timeline.json 的 host.src → {hostrel}")
        log("时间线已写入 " + os.path.join(film, "timeline.json"))

    meta = os.path.join(OUT, "meta.json")
    if os.path.exists(meta):
        shutil.copy(meta, os.path.join(film, "out", "kaggle_meta.json"))
    log(f'完成。渲染：node scripts/render.mjs --dir "{film}" --check')


def cmd_all(argv):
    film = argv[0] if argv else ""
    rest = argv[1:]
    if not film:
        die("用法：python ops/kaggle.py all <片子目录>")
    cmd_pack([film, *rest])
    cmd_push([])
    cmd_run([])
    ok = True
    try:
        cmd_wait([])
    except SystemExit:
        ok = False
    cmd_pull([])
    cmd_apply([film])
    if not ok:
        raise SystemExit(1)


COMMANDS = {
    "init": cmd_init,
    "models": cmd_models,
    "pack": cmd_pack,
    "push": cmd_push,
    "run": cmd_run,
    "status": cmd_status,
    "wait": cmd_wait,
    "pull": cmd_pull,
    "apply": cmd_apply,
    "all": cmd_all,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd not in COMMANDS:
        die(f"不认识的子命令：{cmd}")
    COMMANDS[cmd](sys.argv[2:])


if __name__ == "__main__":
    main()
