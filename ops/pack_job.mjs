#!/usr/bin/env node
// 把一条片子里要上 Kaggle 的东西打包成数据集目录。
//   node ops/pack_job.mjs <片子目录> [--out build/job] [--w 1920] [--from 1] [--to 999999]
//                          [--host assets/host.mp4] [--no-matte] [--no-asr] [--no-clean]
// 产出：build/job/{job.json, dataset-metadata.json, script.json, host.mp4?, clips/*, scripts/*.py}
// 之后由 ops/kaggle.sh push 上传成私有数据集 ws-handoff。
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const argv = process.argv.slice(2);
const opts = { out: 'build/job', w: '1920', from: '1', to: String(10 ** 9), host: null, matte: true, asr: true, clean: true };
const positional = [];
for (let i = 0; i < argv.length; i++) {
  const a = argv[i];
  if (a === '--out') opts.out = argv[++i];
  else if (a === '--w') opts.w = argv[++i];
  else if (a === '--from') opts.from = argv[++i];
  else if (a === '--to') opts.to = argv[++i];
  else if (a === '--host') opts.host = argv[++i];
  else if (a === '--no-matte') opts.matte = false;
  else if (a === '--no-asr') opts.asr = false;
  else if (a === '--no-clean') opts.clean = false;
  else positional.push(a);
}
const film = positional[0] ? path.resolve(positional[0]) : null;
if (!film) {
  console.error('用法: node ops/pack_job.mjs <片子目录> [--w 1920] [--from 1] [--to 999999] [--host assets/host.mp4]');
  process.exit(2);
}
if (!fs.existsSync(path.join(film, 'script.json'))) {
  console.error(`${film} 里没有 script.json，不像片子目录。`);
  process.exit(2);
}

const out = path.resolve(opts.out);
fs.rmSync(out, { recursive: true, force: true });
fs.mkdirSync(out, { recursive: true });

// 口播素材：assets/clips/<name>/*.jpg（footage.py extract 的产物）
const clipsDir = path.join(film, 'assets', 'clips');
const clips = [];
if (fs.existsSync(clipsDir)) {
  for (const e of fs.readdirSync(clipsDir, { withFileTypes: true })) {
    if (!e.isDirectory()) continue;
    const d = path.join(clipsDir, e.name);
    if (fs.readdirSync(d).some(f => /\.jpe?g$/i.test(f))) clips.push(e.name);
  }
}
for (const c of clips) fs.cpSync(path.join(clipsDir, c), path.join(out, 'clips', c), { recursive: true });
fs.copyFileSync(path.join(film, 'script.json'), path.join(out, 'script.json'));

// 口播整段视频（可替换 script.json 的 host 路径）
let host = opts.host;
if (!host) {
  for (const c of ['assets/host.mp4', 'host.mp4', 'assets/host_raw.mp4']) {
    if (fs.existsSync(path.join(film, c))) { host = c; break; }
  }
}
if (host) fs.copyFileSync(path.resolve(film, host), path.join(out, 'host.mp4'));

// 让 Kaggle 自己带脚本，不依赖它去 clone 仓库
fs.mkdirSync(path.join(out, 'scripts'), { recursive: true });
for (const f of ['matte.py', 'matte_clean.py', 'host_timeline.py']) {
  fs.copyFileSync(path.join(ROOT, 'scripts', f), path.join(out, 'scripts', f));
}

const job = {
  film: path.basename(film),
  created: new Date().toISOString(),
  w: Number(opts.w),
  clean: opts.clean,
  matte: opts.matte ? clips.map(n => ({ name: n, src: `clips/${n}`, dst: `cut/${n}`, from: Number(opts.from), to: Number(opts.to) })) : [],
  asr: (opts.asr && host) ? { video: 'host.mp4', script: 'script.json', tail: 0.8 } : null,
};
fs.writeFileSync(path.join(out, 'job.json'), JSON.stringify(job, null, 1));

const user = process.env.KAGGLE_USERNAME || '__USER__';
fs.writeFileSync(path.join(out, 'dataset-metadata.json'), JSON.stringify({
  title: 'ws-handoff',
  id: `${user}/ws-handoff`,
  licenses: [{ name: 'other' }],
}, null, 1));

const du = d => fs.readdirSync(d, { withFileTypes: true }).reduce((s, e) => {
  const p = path.join(d, e.name);
  return s + (e.isDirectory() ? du(p) : fs.statSync(p).size);
}, 0);
const mb = n => (n / 1024 / 1024).toFixed(1) + ' MB';

console.log(`片子：${film}`);
console.log(`抠像：${job.matte.length} 段${clips.length ? '（' + clips.join(', ') + '）' : ''}`);
console.log(`ASR ：${job.asr ? 'host.mp4 + script.json' : '不做'}`);
console.log(`输出：${out}  ${mb(du(out))}`);
if (!job.matte.length && !job.asr) console.log('注意：既没有 clips 也没有 host.mp4，这次没有活可干。');
console.log('下一步：bash ops/kaggle.sh push');
