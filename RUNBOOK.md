# Codespaces + Kaggle 作战手册

这条流水线只解决一件事：**你的笔记本不用扛渲染，也不用扛 GPU。**
Codespaces 当“办公室”（写稿、跑 agent、Playwright 逐帧渲染、ffmpeg 混音），Kaggle 当“GPU 机房”（只跑抠像和口播对齐）。

```
你的浏览器
   │
   ├─ GitHub Codespaces（4 核，持久盘）──────────────┐
   │    写 script.json / film.js                      │
   │    render.mjs --check / --sheet / --video        │
   │    edge-tts 配音、mix.py 混音                     │
   │         │                                        │
   │         │ ① pack：clips + host.mp4 + script.json  │
   │         ▼                                        │
   │    Kaggle Dataset（私有 ws-handoff）              │
   │         │                                        │
   │         │ ② kaggle kernels push                  │
   │         ▼                                        │
   │    Kaggle GPU（T4）：matte.py + host_timeline.py  │
   │         │                                        │
   │         │ ③ result.zip（cut/* + timeline.json）   │
   │         ▼                                        │
   │    build/out ──► 自动写回片子目录                  │
   └──────────────────────────────────────────────────┘
```

## 分工

| 环节 | 在哪跑 | 为什么 |
|---|---|---|
| 选题、文案、导演表 | Codespaces（或本地） | 不吃算力，要 agent 和编辑器 |
| 素材下载、抽帧、新闻截图 | Codespaces | yt-dlp / Playwright；Azure IP 下 YouTube 容易 403，尽量本地下好再传 |
| 逐帧渲染 `render.mjs` | Codespaces | 纯 CPU，4 核够；1080p 一条 1 分钟片约 20–40 分钟 |
| 抠人 `matte.py` | **Kaggle T4** | ISNet 约 0.25 秒/帧；CPU 要 2–5 秒/帧 |
| 口播逐字对齐 `host_timeline.py` | **Kaggle** | faster-whisper；默认走 CPU int8，1–3 分钟口播够用 |
| 混音 `mix.py` | Codespaces | ffmpeg |
| 成片检查 | Codespaces | `--check` / `--sheet` / 抽帧对比 |

## 一次性准备（约 20 分钟）

### 1. 建自己的仓库

这个目录已经是 git 仓库，并且已经提交好了（`Add Codespaces + Kaggle ops pipeline`）。在你的 GitHub 上新建一个**空**仓库（建议 Private），然后：

```bash
git remote rename origin upstream    # 原来的 origin 指向上游作者
git remote add origin https://github.com/<你的用户名>/wallstreet-explainer.git
git branch -M main
git push -u origin main
```

> 如果之前已经改过 remote，`git remote rename` 会报“No such remote”；直接 `git remote set-url origin <你的仓库>` 即可。

### 2. 开 Codespace

仓库页 → **Code** → **Codespaces** → **Create codespace on main** → 机型选 **4-core**（2 核渲染会明显慢）。

首次启动会自动跑 `.devcontainer/setup.sh`：apt 装 ffmpeg、pip 依赖、Playwright Chromium、拉字体。大约 5–10 分钟。

### 3. 配 Kaggle 凭据

Kaggle → 右上头像 → **Settings** → **API** → **Create New Token**，下载 `kaggle.json`（里面有 `username` 和 `key`）。

在 GitHub 仓库 → **Settings** → **Secrets and variables** → **Codespaces**，加两个 secret：

- `KAGGLE_USERNAME`
- `KAGGLE_KEY`

重建/重启 Codespace 后，终端里：

```bash
bash ops/kaggle.sh init
```

### 4. 建模型数据集（只一次）

```bash
bash ops/kaggle.sh models
```

会下载 ISNet（178MB）和 faster-whisper-small（约 500MB），创建私有数据集 `ws-models`。之后每条片都复用它，不用再传，Kaggle 每次跑也不用再下载模型。

### 5. 字体自检

```bash
bash ops/fetch_fonts.sh --check
```

必须齐：`BebasNeue-Regular.ttf`、`AlimamaShuHeiTi-Bold.ttf`、`MiSans-{Regular,Medium,Semibold,Bold}.ttf`、`Montserrat-VF.ttf`、`Montserrat-Italic-VF.ttf`。
脚本能自动下大部分；阿里妈妈数黑体若失败，去 https://www.alibabafonts.com/#/font 下载后放进 `fonts/`。

## 每条片的流程

### A. 正常做片（前 6 站都在 Codespaces）

```bash
# 1. 建片
node scripts/new_film.mjs films/<片子名>

# 2. 写 films/<片子名>/script.json，然后重算时间线
node scripts/timeline_stub.mjs films/<片子名>/script.json

# 3. 写 film.js，然后查镜头表 / 看三帧拼图
node scripts/render.mjs --dir films/<片子名> --check
node scripts/render.mjs --dir films/<片子名> --sheet

# 4. 720p 预览
node scripts/render.mjs --dir films/<片子名> --video --h 720
```

### B. 有真人/数字人口播时，把重活丢给 Kaggle

把口播整段放在 `films/<片子名>/assets/host.mp4`，口播抽帧放在 `films/<片子名>/assets/clips/host/0001.jpg…`（`footage.py extract` 的产物）。然后：

```bash
bash ops/kaggle.sh all films/<片子名>
```

它依次做：

1. `pack_job.mjs` 收集 `assets/clips/*`、`host.mp4`、`script.json`、三个 Python 脚本 → `build/job/`
2. 上传为私有数据集 `ws-handoff`（版本化）
3. `kaggle kernels push` 推 `ws-worker`（T4，9 小时上限）
4. 每 30 秒查状态，最多等 4 小时
5. `kaggle kernels output` 取回 `result.zip`
6. 解包，把 `cut/*` 写进 `films/<片子名>/assets/cut/`，把 `timeline.json` 写回片子根目录，并把 `host.src` 改成 `assets/host.mp4`

只跑其中一段（先试 20 秒）：

```bash
bash ops/kaggle.sh pack films/<片子名> --from 12 --to 160
bash ops/kaggle.sh push
bash ops/kaggle.sh run
bash ops/kaggle.sh wait
bash ops/kaggle.sh pull
bash ops/kaggle.sh apply films/<片子名>
```

预览阶段想省流量，抠像宽度降到 1280：

```bash
bash ops/kaggle.sh all films/<片子名> --w 1280
```

### C. 收尾

```bash
node scripts/render.mjs --dir films/<片子名> --check
node scripts/render.mjs --dir films/<片子名> --sheet
node scripts/render.mjs --dir films/<片子名> --video --h 1080
# 配音 / 混音按 SKILL.md 第 5、8 站
```

## 传文件的协议

不用手动下 zip。两边约定：

| 位置 | 内容 |
|---|---|
| `build/job/job.json` | `{film, w, clean, matte:[{src,dst,from,to}], asr:{video,script,tail}}` |
| `build/job/clips/<name>/` | 待抠帧 `0001.jpg…` |
| `build/job/host.mp4` | 口播整段 |
| `build/job/script.json` | 文案（ASR 对齐用） |
| `build/job/scripts/*.py` | 让 Kaggle 自带脚本，不 clone 仓库 |
| Kaggle 输出 `result.zip` | `cut/<name>/{0001.png, box.json}` + `timeline.json` + `meta.json` |

`meta.json` 里有耗时、是否真的用上 CUDA、以及每段错误。取回后也会复制一份到 `films/<片子名>/out/kaggle_meta.json`。

## 成本与时间

- **Codespaces 4-core**：$0.36/小时；免费额度约 120 core-hours/月（4 核 ≈ 30 小时）。默认 30 分钟闲置自动停，文件不丢。
- **Kaggle**：免费；GPU 每周约 30 小时，单次 9 小时。
- 一条 60–90 秒片：抠像 200–400 帧约 1–3 分钟（T4），ASR 1–2 分钟，720p 渲染 10–20 分钟，1080p 20–40 分钟。

## 故障排查

| 现象 | 原因 / 办法 |
|---|---|
| `kaggle: command not found` | `pip install kaggle`；然后重开终端 |
| `401 Unauthorized` | secret 名字必须是 `KAGGLE_USERNAME` / `KAGGLE_KEY`；改完 secret 要重启 Codespace |
| `kernels push` 报 dataset 不存在 | 先 `bash ops/kaggle.sh push`，再 `run` |
| kernel 秒失败 | 看 `bash ops/kaggle.sh pull` 后的 `meta.json`；最常见是 `ws-models` 没建 |
| kernel 报联网 / 403 | Kaggle 账号要先做手机验证：Settings → Phone Verification |
| `ws-models` 第一次上传慢 | 约 660MB，只传一次；以后每条片只传 `ws-handoff` 的素材 |
| 抠像跑在 CPU | `meta.json` 里 `cuda:false`；Kaggle 设置里确认 Accelerator=GPU T4 x2 |
| ASR 对不上 | `timeline.json` 生成时会打印“对上 x%”；低于 80% 说明 script.json 和口播不一致 |
| `--check` 报时间线过期 | 改过 `script.json` 后重跑 `timeline_stub.mjs`；有配音则重跑 ASR |
| Chromium 起不来 | `.devcontainer/setup.sh` 已给 `render.mjs` 补 `--no-sandbox`；若仓库更新覆盖了，重跑 setup |
| 字体缺失、字变系统体 | `bash ops/fetch_fonts.sh --check`，按缺的补 |

## 已知取舍

- **不是实时集群**：Kaggle 排队 1–5 分钟很正常；`wait` 上限 4 小时。
- **数据集是快照**：每次 `push` 生成新版本，旧版本不会自动删。
- **隐私**：`ws-handoff` / `ws-models` / `ws-worker` 都建成私有；素材仍建议只放有授权的内容。
- **agent 不在 Kaggle 上**：agent 只在 Codespaces 里指挥；Kaggle 只执行两个固定脚本。这是故意的，避免在无人工看护的机器上跑开放式 agent。
- **1080p 不一定需要 Kaggle**：渲染是 CPU 活，Codespaces 4 核可跑；Kaggle 只省抠像和 ASR 的时间。
