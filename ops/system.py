#!/usr/bin/env python3
"""系统的开与关：Codespaces（办公室）+ Kaggle（GPU 机房）。

    python ops/system.py up        # 启动：Codespace 不存在就建，存在就开；顺手验 Kaggle
    python ops/system.py down      # 关闭：停 Codespace；确认 Kaggle 没有正在跑的任务
    python ops/system.py status    # 两边现在什么状态
    python ops/system.py sh "<命令>"   # 在 Codespace 里执行一条命令（远程）
    python ops/system.py put <本地> <远端>   # 传文件上去
    python ops/system.py get <远端> <本地>   # 取文件下来

计费模型（重要）：
  * Codespaces 只在 **运行** 时扣 core-hours；停止后只剩存储（15GB/月额度）。
    → 干完活 `down` 就行；一个月不用想彻底释放，`down --delete`。
  * Kaggle 的 GPU 配额只在 **kernel 运行** 时消耗，跑完自动停，没事可关。
    → `down` 会检查有没有还挂着的 kernel；排队/运行中的要人工在网页上 Stop。
"""
import json
import os
import shutil
import subprocess
import sys
import time

REPO = os.environ.get("WS_REPO", "jackding2008-create/wallstreet-explainer")
NAME = os.environ.get("WS_CODESPACE", "wallstreet")
MACHINE = os.environ.get("WS_MACHINE", "standardLinux32gb")  # 4 核 16GB
IDLE = os.environ.get("WS_IDLE", "30m")
KREF = os.environ.get("WS_KERNEL", "ws-worker")


def log(msg):
    print(f"== {msg} ==", flush=True)


def die(msg):
    print(f"错误：{msg}", file=sys.stderr, flush=True)
    raise SystemExit(1)


def gh_bin():
    p = shutil.which("gh")
    if p:
        return p
    for c in (
        r"C:\Program Files\GitHub CLI\gh.exe",
        r"C:\Program Files (x86)\GitHub CLI\gh.exe",
        os.path.expanduser(r"~\scoop\shims\gh.exe"),
    ):
        if os.path.exists(c):
            return c
    die("没有 gh CLI。装一个：winget install --id GitHub.cli -e  或  brew install gh")


def gh(*args, check=True, quiet=False):
    cmd = [gh_bin(), *map(str, args)]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                       encoding="utf-8", errors="replace")
    out = (p.stdout or "").strip()
    if p.returncode != 0 and check:
        print(out, file=sys.stderr)
        die(f"gh 失败：{' '.join(args[:2])}")
    if not quiet and out:
        print(out, flush=True)
    return out


def kaggle(*args, check=False, quiet=True):
    cmd = [sys.executable, "-m", "kaggle", *map(str, args)]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                       encoding="utf-8", errors="replace")
    if p.returncode != 0 and check:
        die(f"kaggle 失败：{' '.join(args[:2])}\n{p.stdout}")
    return (p.stdout or "").strip()


def kuser():
    u = os.environ.get("KAGGLE_USERNAME")
    if u:
        return u
    for line in kaggle("config", "view").splitlines():
        if line.strip().startswith("- username:"):
            return line.split(":", 1)[1].strip()
    die("拿不到 Kaggle 用户名")


# ------------------------------------------------------------------ codespaces


def list_spaces():
    raw = gh("codespace", "list", "-R", REPO, "--json",
             "name,state,displayName,machineName,lastUsedAt", quiet=True)
    try:
        return json.loads(raw or "[]")
    except json.JSONDecodeError:
        return []


def find_space(spaces):
    for s in spaces:
        if s.get("displayName") == NAME:
            return s
    return spaces[0] if spaces else None


def cmd_up(argv):
    gh("auth", "status")
    spaces = list_spaces()
    cs = find_space(spaces)
    if not cs:
        log(f"没有 Codespace，建一个（{MACHINE}）：{REPO}")
        gh("codespace", "create", "-R", REPO, "-b", "main", "-m", MACHINE,
           "--display-name", NAME, "--idle-timeout", IDLE, quiet=True)
        spaces = list_spaces()
        cs = find_space(spaces)
        if not cs:
            die("Codespace 建了但列表里看不到，稍等再试")
    elif cs["state"] == "Shutdown":
        log(f"启动 {cs['name']}")
        gh("codespace", "start", "-c", cs["name"], quiet=True)
    elif cs["state"] == "Available":
        log(f"{cs['name']} 已经在跑")

    for _ in range(60):  # 最多等 10 分钟
        cs = find_space(list_spaces())
        state = cs.get("state") if cs else "?"
        print(f"  Codespace: {state}", flush=True)
        if state == "Available":
            break
        if state in ("Failed", "Unknown"):
            die("Codespace 起不来，看 gh cs list 或网页日志")
        time.sleep(10)

    # Kaggle 这边：验登录 + 数据集在
    u = kuser()
    log(f"Kaggle 用户：{u}")
    for slug in ("ws-models", "ws-handoff"):
        if f"{u}/{slug}" not in kaggle("datasets", "list", "-m", "--page-size", "50"):
            print(f"  警告：数据集 {u}/{slug} 还不存在", flush=True)

    print()
    print("就绪。开工命令：")
    print(f'  python ops/system.py sh "cd ~/wallstreet-explainer && git pull && node scripts/render.mjs --dir films/<片名> --check"')
    print(f"  gh codespace ssh -c {cs['name']}   # 想自己进去看看")


def cmd_down(argv):
    spaces = list_spaces()
    cs = find_space(spaces)
    killed = 0
    if cs:
        if cs["state"] not in ("Shutdown",):
            log(f"停止 {cs['name']}（{cs['state']}）")
            gh("codespace", "stop", "-c", cs["name"], check=False, quiet=True)
            killed += 1
        else:
            log(f"{cs['name']} 已经是停止状态")
    else:
        log("没有 Codespace")

    if "--delete" in argv and cs:
        log(f"删除 {cs['name']}（释放存储额度）")
        gh("codespace", "delete", "-c", cs["name"], "--force", check=False, quiet=True)

    st = kaggle("kernels", "status", f"{kuser()}/{KREF}").lower()
    log(f"Kaggle 上的 {KREF}：{st or '没有这个 kernel'}")
    live = any(w in st for w in ("running", "queued", "provisioning"))
    if live:
        print("  注意：这个 kernel 还在跑/排队，配额还在烧。", flush=True)
        print(f"  去 https://www.kaggle.com/code/{kuser()}/{KREF} 点 Stop，或等它自己结束。", flush=True)

    print()
    print("已关闭。" + ("（存储仍在计费：15GB/月额度）" if cs and "--delete" not in argv else ""))
    if killed:
        print("下次开工：跟我说一声，我跑 python ops/system.py up")


def cmd_status(argv):
    spaces = list_spaces()
    cs = find_space(spaces)
    if cs:
        print(f"Codespace  {cs['name']}  {cs['state']}  ({cs.get('machineName')})  最后使用 {cs.get('lastUsedAt')}")
    else:
        print("Codespace  无")
    print(f"Kaggle     {kuser()}/{KREF}  {kaggle('kernels', 'status', f'{kuser()}/{KREF}') or '无'}")
    ds = kaggle("datasets", "list", "-m", "--page-size", "50")
    for slug in ("ws-models", "ws-handoff"):
        print(f"  {slug}: {'有' if slug in ds else '缺失'}")


# ------------------------------------------------------------- remote commands


def cmd_sh(argv):
    if not argv:
        die('用法：python ops/system.py sh "<命令>"')
    cs = find_space(list_spaces())
    if not cs or cs["state"] != "Available":
        die("Codespace 没在跑，先 up")
    cmd = " ".join(argv)
    p = subprocess.run([gh_bin(), "codespace", "ssh", "-c", cs["name"], "--", cmd])
    raise SystemExit(p.returncode)


def cmd_put(argv):
    if len(argv) < 2:
        die("用法：python ops/system.py put <本地> <远端相对路径>")
    cs = find_space(list_spaces())
    if not cs:
        die("没有 Codespace")
    gh("codespace", "cp", "-c", cs["name"], "-r", argv[0], f"remote:{argv[1]}")


def cmd_get(argv):
    if len(argv) < 2:
        die("用法：python ops/system.py get <远端相对路径> <本地>")
    cs = find_space(list_spaces())
    if not cs:
        die("没有 Codespace")
    gh("codespace", "cp", "-c", cs["name"], "-r", f"remote:{argv[0]}", argv[1])


COMMANDS = {
    "up": cmd_up,
    "down": cmd_down,
    "status": cmd_status,
    "sh": cmd_sh,
    "put": cmd_put,
    "get": cmd_get,
}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(0)
    fn = COMMANDS.get(sys.argv[1])
    if not fn:
        die(f"不认识的子命令：{sys.argv[1]}")
    fn(sys.argv[2:])
