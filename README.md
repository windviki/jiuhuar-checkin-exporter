# jiuhuar-checkin-exporter 🍺

> **酒花儿停运数据抢救工具** —— 在服务器彻底关闭之前，把你自己的打卡历史完整导出留底。
> Rescue **your own** 酒花儿 (Jiuhuar) check-in history before the servers go dark.

![export gallery](docs/gallery-screenshot.png)

---

## 目录 / Contents
- [✨ 功能特性](#-功能特性)
- [📦 输出内容](#-输出内容)
- [🚀 快速开始](#-快速开始小白友好)
- [🔑 什么时候需要密码](#-什么时候需要密码)
- [❓ 常见问题](#-常见问题)
- [⚙️ 工作原理](#️-工作原理)
- [⚠️ 免责声明](#️-免责声明)
- [English documentation](#english)

---

## ✨ 功能特性

一条命令，导出你账号里的**全部**数据：

- 📝 **全部打卡**：酒款点评 + 酒吧点评，含时间、四维评分（香气/味道/外观/感受）、总评分、评论文本、风味标签、点赞回复数
- 🖼️ **全部图片原尺寸下载**：打卡照片、酒款标签原图（非缩略图）、酒吧照片、头像
- 🍺 **酒款完整信息**：中英文名、酒厂（中英文+简介）、国家、风格、ABV/IBU、官方评分、酒款介绍
- 🏠 **酒吧完整信息**：省市区、地址、营业时间、评分、简介（已下架的酒吧用打卡时的快照兜底）
- 👥 **关注与粉丝**：计数总是导出；**人员名单**（昵称+头像+关注日期）需要登录 token（见[密码说明](#-什么时候需要密码)）
- 🎨 **可视化画廊** `index.html`：双击即可浏览的深色相册，顶部是关注/粉丝头像墙，下面是全部打卡卡片
- 📊 **结构化数据**：完整 JSON + Excel 可直接打开的 CSV（UTF-8 BOM）
- 🛡️ **无需登录即可导出绝大部分数据**（打卡/图片/酒款/酒吧/计数都是公开数据）

## 📦 输出内容

运行后在 `output/`（或 `--out` 指定目录）生成：

| 文件/目录 | 内容 |
|---|---|
| `index.html` | 深色可视化画廊：关注/粉丝头像墙 + 全部打卡卡片（本地直接打开） |
| `<昵称>_checkins_full.json` | 全部数据的结构化版本（推荐程序读取） |
| `<昵称>_checkins.csv` | 表格版，Excel 双击直接打开（含中英文名/酒厂/酒吧地址等 24 列） |
| `checkins_beer.json` / `checkins_bar.json` | 服务端原始数据（酒款点评/酒吧点评） |
| `beer_details.json` / `breweries.json` / `bars.json` | 酒款、酒厂、酒吧详情（含英文名） |
| `follow_info.json` | 粉丝数/关注数（公开数据） |
| `followers.json` / `following.json` | 粉丝/关注人员名单（昵称+头像+关注日期）——仅在使用 `--token` 时生成 |
| `images/` | 所有图片原尺寸：`checkins/` 打卡照片 · `beers_lg/` 酒款标签原图 · `beers/` 缩略图 · `avatars/` 头像（含名单里每个人） · `bars/` 酒吧图 · `profile/` 你的头像和背景 |
| `run_log.txt` | 本次运行日志 |

> ⚠️ **隐私提醒**：`output/` 是你的个人数据（`user_profile.json` 可能包含绑定手机号），只保存在本地，别上传到网上。仓库的 `.gitignore` 已默认排除。

## 🚀 快速开始（小白友好）

**第 1 步：安装 Python 3.10 或更高版本**
- 官网下载：https://www.python.org/downloads/ （安装时勾选 *Add Python to PATH*）

**第 2 步：下载本工具并安装依赖**
- 点本页面绿色 **Code → Download ZIP**，解压后，在文件夹里打开命令行（地址栏输入 `cmd` 回车），执行：

```bash
pip install -r requirements.txt
```

- 国内网络慢可用清华镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

**第 3 步：一条命令导出**（把 `你的昵称` 换成你的酒花儿昵称）

```bash
python main.py --nickname 你的昵称
```

**第 4 步：查看成果**
- 双击打开 `output/index.html` —— 你的专属啤酒记忆画廊 🍺
- 视数据量，全程约 5–40 分钟（工具会自动控制节奏，对服务器友好）

可选参数：

```bash
python main.py --nickname X --out D:/my_export     # 指定输出目录
python main.py --nickname X --skip-images          # 只导文字不下图
python main.py --nickname X --skip-enrich          # 跳过酒款/酒厂详情
python main.py --nickname X --token <token>        # 追加粉丝/关注名单（见下）
python build_export.py ./output                    # 只重新生成 JSON/CSV/画廊
```

## 🔑 什么时候需要密码

**绝大部分功能不需要密码，也不需要登录**：打卡、评论、图片、酒款/酒厂/酒吧信息、粉丝/关注**计数**，全部可以匿名导出。

**只有一项功能需要登录**：粉丝/关注的**人员名单**（谁关注了你、你关注了谁）。服务端把这个接口设为仅登录可见。

想导名单的话（完全可选）：

```bash
# 1) 用你的账号密码换取一次性 token（手机号+密码）
python login.py --username 13500000000 --password '你的密码'     # 成功后生成 token.txt

# 2) 带着 token 重新导出（或补导）
python main.py --nickname 你的昵称 --token $(cat token.txt)
```

**关于密码与安全，说清楚三件事**：

1. **密码不保存**：`login.py` 只在你的电脑内存里把密码换成一次 token，密码**不会**写进任何文件、不会发送到除酒花儿服务器之外的任何地方；git 仓库也永远不含密码。
2. **token 是登录凭证**：换取的 `token.txt` 请保存在自己电脑上，勿分享给他人。
3. **登录不保证可用**：平台已停运——Android 端登录已损坏、网页登录已下线、短信网关已停止。实测密码登录接口**目前仍有效**（2026-11 验证），但随时可能失效。登录失败**不影响**其他所有数据的导出，工具会自动跳过名单并继续。

## ❓ 常见问题

- **提示 nickname not found**：昵称需与个人资料完全一致（区分大小写）；也请确认账号主页未隐藏。
- **图片 403 / 下载失败**：工具已内置正确的图片 URL 规则；个别服务器端已删除的图片会记录到 `image_failures.json`。
- **证书错误**：酒花儿服务器证书 2020 年就过期了，工具已自动跳过校验，无需处理。
- **登录失败/收不到短信**：见[密码说明](#-什么时候需要密码)，跳过名单即可。
- **跑一半断网/中断**：直接重新运行即可，已下载的图片自动跳过，不会重复下载。
- **服务器还能撑多久？** 未知。停运服务随时可能彻底关机——**尽早导出**。

## ⚙️ 工作原理

平台已停止用户侧运营（登录已损坏），但后端仍在对外提供**公开数据**，而每个用户的主页及其打卡列表都是公开的——因此无需登录即可导出自己的历史。以下协议事实恢复自最后一个 Android 客户端（v5.8.8）：

- API 基址 `https://napi.jiuhuar.com/api/`，TLS 证书已过期（需跳过校验）
- 请求需模拟 App 头部；`content-type: application/json` 决定返回 JSON，`udid` 同时充当响应加密密钥
- 响应 `{"code":0,"crypted":true,"data":"<base64>"}`，`data` 为 **AES-128/ECB/PKCS7**，密钥就是请求头里的 `udid`（不足16位补0）——密钥完全由客户端自选
- 列表分页用 `lastTime`/`lastTimestamp`（unix 秒）：首页传 `Long.MAX_VALUE`，之后传上一页最后一条的时间；每页 10 条（时间戳必须以整数发送，浮点数会被服务器 400 拒绝）
- 图片（七牛 CDN）：用户照片必须带 `?imageMogr2/auto-orient` 参数（裸链被 WAF 403）；酒款缩略图用 `bg-{id}` 前缀；酒款原图用 `{id}-lg2` 后缀
- 评分字段：`r1=香气 r2=味道 r3=外观 r4=感受 rating=总体`（已与官网交叉验证）
- 主要端点：`user/id`（昵称→uid）· `comment/v3/user`（打卡）· `comment/bar/user`（酒吧点评）· `beer/v3/{id}` · `beer/brewery/{id}` · `bar/{id}` · `follow/followInfo`（计数，公开）· `follow/user/follower|following`（名单，需token）· `signin`（密码换token，不保证可用）

## ⚠️ 免责声明

本工具仅用于导出**你自己的**数据做个人备份/迁移。与酒花儿官方无关；所有商标归其所有者。请控制请求频率（工具已内置限速），服务随时可能永久下线。

---

# English

> Rescue **your own** check-in history from 酒花儿 (Jiuhuar, the Chinese craft-beer app) — ratings, comments, photos, beer & brewery info — even though the app has ended consumer operation and login is broken.

## ✨ Features

One command exports **everything** in your account:

- 📝 **All check-ins** (beer + bar): timestamps, 4-dimension ratings (aroma/taste/look/feel), overall score, comments, flavor tags, likes/replies
- 🖼️ **All images at original resolution**: check-in photos, beer label art (full-size, not thumbnails), bar photos, avatars
- 🍺 **Full beer info**: Chinese **and English** names, brewery (CN/EN + description), country, style, ABV/IBU, official rating
- 🏠 **Full bar info**: province/city/district, address, opening hours, rating (delisted bars fall back to the check-in snapshot)
- 👥 **Followers/following**: counts always exported; **name lists** (nickname + avatar + follow date) need a login token (see [passwords](#-when-do-you-need-a-password))
- 🎨 **Browsable gallery** `index.html`: dark-theme album — social avatar wall on top, all check-in cards below
- 📊 **Structured data**: full JSON + Excel-ready CSV (UTF-8 BOM)
- 🛡️ **No login needed for almost everything** (check-ins/photos/beers/bars/counts are public data)

## 📦 Output

| File | Content |
|---|---|
| `index.html` | Dark gallery: social avatar wall + all check-in cards (opens locally) |
| `<nick>_checkins_full.json` | Normalized full data |
| `<nick>_checkins.csv` | Spreadsheet, 24 columns, opens directly in Excel |
| `checkins_beer.json` / `checkins_bar.json` | Raw API data |
| `beer_details.json` / `breweries.json` / `bars.json` | Beer / brewery / bar details (incl. English names) |
| `follow_info.json` | follower/following counts (public) |
| `followers.json` / `following.json` | Name lists with avatars & follow dates — only with `--token` |
| `images/` | Everything at original resolution: `checkins/` `beers_lg/` `beers/` `avatars/` (incl. everyone in your lists) `bars/` `profile/` |
| `run_log.txt` | What the run did |

> ⚠️ **Privacy**: `output/` is your personal data (`user_profile.json` may contain your bound phone number). Keep it local; `.gitignore` already excludes it.

## 🚀 Quick start

1. Install **Python 3.10+**: https://www.python.org/downloads/ (check *Add Python to PATH*)
2. Download this repo (green **Code → Download ZIP**), open a terminal in the folder (type `cmd` in the address bar), then:

```bash
pip install -r requirements.txt
```

3. Export (replace `YOUR_NICKNAME` with your jiuhuar nickname):

```bash
python main.py --nickname YOUR_NICKNAME
```

4. Open `output/index.html` — your personal beer memory gallery 🍺 (takes 5–40 min depending on data size; the tool rate-limits itself to stay gentle)

Optional flags: `--out DIR`, `--skip-images`, `--skip-enrich`, `--token <t>`, and `python build_export.py ./output` to rebuild JSON/CSV/HTML only.

## 🔑 When do you need a password

**You don't, for almost everything.** Check-ins, comments, photos, beer/brewery/bar info and follower **counts** are public and export anonymously.

**Only one feature needs a login**: the follower/following **name lists**. The endpoint requires an authenticated token.

Optional, if you want the lists:

```bash
python login.py --username 13500000000 --password 'your-password'   # -> token.txt
python main.py --nickname YOUR_NICKNAME --token $(cat token.txt)
```

Three things to be clear about:

1. **Your password is never saved.** `login.py` exchanges it for a one-time token in local memory only — it is never written to any file and never sent anywhere except the jiuhuar server; the git repo never contains it.
2. **The token is a credential.** Keep `token.txt` on your machine — do not share it.
3. **Login is not guaranteed to work.** The platform has ended operation: Android login is broken, the web login was removed, and the SMS gateway is dead. Password login still worked when tested (Nov 2026) but may stop any day. If it fails, the tool simply skips the lists and exports everything else.

## ❓ FAQ

- **nickname not found** — the nickname must match exactly (case-sensitive); hidden profiles can't be read.
- **Certificate errors** — the server cert expired in 2020; the tool already skips verification.
- **Some images fail** — a few are deleted server-side; they're listed in `image_failures.json`.
- **Interrupted run** — just run again; already-downloaded images are skipped automatically.
- **How long will the server last?** Unknown — export sooner rather than later.

## ⚙️ How it works

The app ended consumer operation (login broken), but the backend still serves **public** data, and every profile with its check-in list is public — so no login is needed to export your own history. Recovered protocol facts (from the last Android client v5.8.8):

- API base `https://napi.jiuhuar.com/api/`; TLS cert expired in 2020 (skip verification)
- App-shaped headers required; `content-type: application/json` selects JSON, and the `udid` header doubles as the response key
- Responses: `{"code":0,"crypted":true,"data":"<base64>"}` with **AES-128/ECB/PKCS7**, keyed by the request's own `udid` (client-chosen)
- List pagination via `lastTime`/`lastTimestamp` (unix seconds): `Long.MAX_VALUE` first, then the last item's timestamp; 10 per page (send timestamps as ints — floats get HTTP 400)
- Images (Qiniu CDN): user photos need `?imageMogr2/auto-orient` (bare URLs are WAF-blocked); beer thumbs use a `bg-` prefix; beer originals use a `-lg2` suffix
- Ratings: `r1=aroma r2=taste r3=look r4=feel rating=overall` (cross-validated against the website)
- Key endpoints: `user/id`, `comment/v3/user`, `comment/bar/user`, `beer/v3/{id}`, `beer/brewery/{id}`, `bar/{id}`, `follow/followInfo` (public), `follow/user/follower|following` (token), `signin` (may or may not work)

## ⚠️ Disclaimer

For exporting **your own** data for personal backup/migration. Not affiliated with jiuhuar; trademarks belong to their owners. Be gentle with the server (built-in rate limits) — it may go offline permanently at any time. That's exactly why this tool exists.
