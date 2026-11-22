# jiuhuar-checkin-exporter

> 酒花儿停运数据抢救工具：在服务器彻底关闭之前，把你自己的打卡历史完整导出留底。
> Rescue your own jiuhuar check-in history before the servers go dark.

![export gallery](docs/gallery-screenshot.png)

## 目录 / Contents

- [功能特性](#功能特性)
- [输出内容](#输出内容)
- [快速开始](#快速开始)
- [登录与密码说明](#登录与密码说明)
- [常见问题](#常见问题)
- [工作原理](#工作原理)
- [免责声明](#免责声明)
- [English](#english)

## 功能特性

一条命令导出账号内的全部数据：

- 全部打卡：酒款点评与酒吧点评，含时间、四维评分（香气 / 味道 / 外观 / 感受）、总评分、评论文本、风味标签、点赞与回复数
- 全部图片原尺寸下载：打卡照片、酒款标签原图（非缩略图）、酒吧照片、头像
- 酒款完整信息：中英文名、酒厂（中英文与简介）、国家、风格、ABV / IBU、官方评分
- 酒吧完整信息：省市区、地址、营业时间、评分；已下架的酒吧回退使用打卡时的快照
- 关注与粉丝：计数始终导出；人员名单（昵称、头像、关注日期）需要登录，见[登录与密码说明](#登录与密码说明)
- 可视化画廊 `index.html`：本地双击即可浏览的深色相册，顶部为关注 / 粉丝头像墙，下方为全部打卡卡片
- 结构化数据：完整 JSON 与 Excel 可直接打开的 CSV（UTF-8 BOM）
- 无需登录即可导出绝大部分数据：打卡、图片、酒款、酒吧、计数均为公开数据

## 输出内容

运行后在 `output/`（可用 `--out` 指定其他目录）生成：

| 文件 / 目录 | 内容 |
|---|---|
| `index.html` | 深色可视化画廊：关注 / 粉丝头像墙 + 全部打卡卡片 |
| `<昵称>_checkins_full.json` | 全部数据的结构化版本（推荐程序读取） |
| `<昵称>_checkins.csv` | 表格版，Excel 双击直接打开，24 列（含中英文名、酒厂、酒吧地址等） |
| `checkins_beer.json` / `checkins_bar.json` | 服务端原始数据（酒款点评 / 酒吧点评） |
| `beer_details.json` / `breweries.json` / `bars.json` | 酒款、酒厂、酒吧详情（含英文名） |
| `follow_info.json` | 粉丝数 / 关注数（公开数据） |
| `followers.json` / `following.json` | 粉丝 / 关注人员名单——仅在登录后生成 |
| `images/` | 全部图片原尺寸：`checkins/` 打卡照片、`beers_lg/` 酒款标签原图、`beers/` 缩略图、`avatars/` 头像（含名单中每个人）、`bars/` 酒吧图、`profile/` 个人头像与背景 |
| `run_log.txt` | 运行日志 |

隐私提醒：`output/` 是你的个人数据（`user_profile.json` 可能包含绑定手机号），只保存在本地，请勿上传到网上。仓库的 `.gitignore` 已默认排除该目录。

## 快速开始

第 1 步：安装 Python 3.10 或更高版本（官网 <https://www.python.org/downloads/>，安装时勾选 *Add Python to PATH*）。

第 2 步：下载本工具（页面绿色 **Code → Download ZIP**），解压后在文件夹内打开命令行（地址栏输入 `cmd` 回车），安装依赖：

```bash
pip install -r requirements.txt
```

国内网络慢可用清华镜像：`pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple`

第 3 步：导出（把 `你的昵称` 换成你的酒花儿昵称）：

```bash
python main.py --nickname 你的昵称
```

第 4 步：双击打开 `output/index.html` 查看成果。

视数据量全程约 5–40 分钟，工具内置限速，对服务器友好。

常用可选参数：

```bash
python main.py --nickname X --out D:/my_export   # 指定输出目录
python main.py --nickname X --skip-images        # 只导文字，不下载图片
python main.py --nickname X --skip-enrich        # 跳过酒款/酒厂详情
python main.py --nickname X --login              # 交互式登录，追加粉丝/关注名单
python main.py --nickname X --token <token>      # 直接使用已有 token
python build_export.py ./output                  # 只重新生成 JSON/CSV/画廊
```

## 登录与密码说明

**绝大部分功能不需要密码，也不需要登录。** 打卡、评论、图片、酒款 / 酒厂 / 酒吧信息、粉丝与关注计数，全部匿名即可导出。

**只有一项功能需要登录**：粉丝 / 关注的人员名单。服务端将该接口设为仅登录可见。

需要名单时，加 `--login` 运行，按提示输入手机号和密码（密码输入为隐藏显示）：

```bash
python main.py --nickname 你的昵称 --login
手机号 / phone number: 13500000000
密码（输入隐藏）/ password (hidden): ********
```

登录成功后 token 自动保存到当前目录的 `token.txt`，之后的运行可以用 `--token $(cat token.txt)`（Windows 用户：打开 `token.txt` 复制内容，替换命令中的 `<token>`）复用，无需再次输入密码。

关于安全的说明：

1. 密码不保存。密码只在你的电脑内存中一次性换取 token，不会写入任何文件，也不会发送到酒花儿服务器之外的任何地方；git 仓库中永远不含密码。
2. token 等同于登录凭证。`token.txt` 请保存在自己电脑上，勿分享给他人。
3. 登录不保证可用。平台已停运：Android 端登录已损坏、网页登录已下线、短信网关已停止。实测密码登录接口在 2026 年 11 月仍有效，但随时可能失效。登录失败不影响其他数据导出，工具会自动跳过名单并继续。

## 常见问题

- 提示 nickname not found：昵称需与个人资料完全一致（区分大小写）；也请确认账号主页未设置为隐藏。
- 图片下载失败：工具已内置正确的图片 URL 规则；个别服务器端已删除的图片会记录在 `image_failures.json`。
- 证书错误：酒花儿服务器证书 2020 年已过期，工具自动跳过校验，无需处理。
- 登录失败或收不到短信：见上文登录说明，跳过名单即可。
- 中断后重跑：直接重新运行即可，已下载的图片会自动跳过，不会重复下载。
- 服务器还能撑多久：未知，建议尽早导出。

## 工作原理

平台已停止用户侧运营（登录损坏），但后端仍对外提供公开数据，而每个用户的主页及其打卡列表均为公开——因此无需登录即可导出自己的历史。以下协议事实恢复自最后一个 Android 客户端（v5.8.8）：

- API 基址 `https://napi.jiuhuar.com/api/`，TLS 证书已过期（需跳过校验）
- 请求需模拟 App 头部；`content-type: application/json` 决定返回 JSON；`udid` 同时充当响应加密密钥
- 响应 `{"code":0,"crypted":true,"data":"<base64>"}`，`data` 为 AES-128/ECB/PKCS7 加密，密钥即请求头中的 `udid`（不足 16 位补 0），密钥完全由客户端自选
- 列表分页使用 `lastTime` / `lastTimestamp`（unix 秒）：首页传 `Long.MAX_VALUE`，之后传上一页最后一条的时间；每页 10 条；时间戳必须以整数发送（浮点数会被服务器以 HTTP 400 拒绝）
- 图片（七牛 CDN）：用户照片必须带 `?imageMogr2/auto-orient` 参数（裸链被 WAF 拦截）；酒款缩略图使用 `bg-{id}` 前缀；酒款原图使用 `{id}-lg2` 后缀
- 评分字段：`r1=香气 r2=味道 r3=外观 r4=感受 rating=总体`（与官网交叉验证）
- 主要端点：`user/id`（昵称转 uid）、`comment/v3/user`（打卡）、`comment/bar/user`（酒吧点评）、`beer/v3/{id}`、`beer/brewery/{id}`、`bar/{id}`、`follow/followInfo`（计数，公开）、`follow/user/follower|following`（名单，需 token）、`signin`（密码换 token，不保证可用）

## 免责声明

本工具仅用于导出自己的数据做个人备份或迁移。与酒花儿官方无关，所有商标归其所有者所有。请勿高频请求（工具已内置限速）；服务随时可能永久下线。

---

## English

> Rescue your own check-in history from jiuhuar (酒花儿, the Chinese craft-beer app) — ratings, comments, photos, beer and brewery info — even though the app has ended consumer operation and login is broken.

### Features

One command exports everything in your account:

- All check-ins (beer + bar): timestamps, four-dimension ratings (aroma / taste / look / feel), overall score, comments, flavor tags, likes and replies
- All images at original resolution: check-in photos, beer label art (full size, not thumbnails), bar photos, avatars
- Full beer info: Chinese and English names, brewery (CN/EN + description), country, style, ABV/IBV, official rating
- Full bar info: province/city/district, address, opening hours, rating; delisted bars fall back to the check-in snapshot
- Followers/following: counts always exported; name lists (nickname, avatar, follow date) require login (see below)
- Browsable gallery `index.html`: dark-theme album with a social avatar wall on top and all check-in cards below, opens locally
- Structured data: full JSON plus an Excel-ready CSV (UTF-8 BOM)
- No login needed for almost everything: check-ins, photos, beers, bars and counts are public data

### Output

| File | Content |
|---|---|
| `index.html` | Dark gallery: social avatar wall + all check-in cards |
| `<nick>_checkins_full.json` | Normalized full data |
| `<nick>_checkins.csv` | Spreadsheet, 24 columns, opens directly in Excel |
| `checkins_beer.json` / `checkins_bar.json` | Raw API data |
| `beer_details.json` / `breweries.json` / `bars.json` | Beer / brewery / bar details (incl. English names) |
| `follow_info.json` | Follower/following counts (public) |
| `followers.json` / `following.json` | Name lists with avatars and follow dates — only when logged in |
| `images/` | Everything at original resolution: `checkins/`, `beers_lg/`, `beers/`, `avatars/` (incl. everyone in your lists), `bars/`, `profile/` |
| `run_log.txt` | Run log |

Privacy note: `output/` is your personal data (`user_profile.json` may contain your bound phone number). Keep it local; the repo's `.gitignore` already excludes it.

### Quick start

1. Install Python 3.10+ (<https://www.python.org/downloads/>, check *Add Python to PATH*).
2. Download this repo (green **Code → Download ZIP**), open a terminal in the folder, then:

   ```bash
   pip install -r requirements.txt
   ```

3. Export (replace `YOUR_NICKNAME` with your jiuhuar nickname):

   ```bash
   python main.py --nickname YOUR_NICKNAME
   ```

4. Open `output/index.html`.

Depending on data size the full run takes 5–40 minutes; the tool rate-limits itself to stay gentle on the server.

Common optional flags:

```bash
python main.py --nickname X --out D:/my_export   # custom output directory
python main.py --nickname X --skip-images        # text only, no photos
python main.py --nickname X --skip-enrich        # skip beer/brewery details
python main.py --nickname X --login              # interactive login for name lists
python main.py --nickname X --token <token>      # reuse an existing token
python build_export.py ./output                  # rebuild JSON/CSV/HTML only
```

### Login and passwords

**You do not need a password for almost everything.** Check-ins, comments, photos, beer/brewery/bar info and follower/following counts export anonymously.

**Only one feature needs a login**: the follower/following name lists. That endpoint requires an authenticated token.

Add `--login` and follow the prompts (password input is hidden):

```bash
python main.py --nickname YOUR_NICKNAME --login
phone number: 13500000000
password (input hidden): ********
```

On success the token is saved to `token.txt` in the current directory. Later runs can reuse it with `--token $(cat token.txt)` (Windows: open `token.txt`, copy the string and paste it in place of `<token>`), so you never need to type the password again.

Security notes:

1. The password is never saved. It is exchanged for a token once, in local memory only — never written to any file and never sent anywhere except the jiuhuar server. The git repository never contains it.
2. The token is a credential. Keep `token.txt` on your machine and do not share it.
3. Login is not guaranteed to work. The platform has ended operation: Android login is broken, the web login was removed, and the SMS gateway is dead. Password login still worked when tested (Nov 2026) but may stop any day. A failed login does not affect anything else — the tool skips the lists and continues.

### FAQ

- "nickname not found" — the nickname must match exactly (case-sensitive); hidden profiles cannot be read.
- Failed image downloads — a few images are deleted server-side; they are listed in `image_failures.json`.
- Certificate errors — the server certificate expired in 2020; the tool already skips verification.
- Interrupted runs — run again; already-downloaded images are skipped automatically.
- How long will the server last — unknown; export sooner rather than later.

### How it works

The app ended consumer operation (login broken), but the backend still serves public data, and every profile with its check-in list is public — so exporting your own history needs no login. Recovered protocol facts (from the last Android client, v5.8.8):

- API base `https://napi.jiuhuar.com/api/`; TLS certificate expired in 2020 (skip verification)
- App-shaped headers are required; `content-type: application/json` selects JSON; the `udid` header doubles as the response key
- Responses: `{"code":0,"crypted":true,"data":"<base64>"}` — AES-128/ECB/PKCS7, keyed by the request's own `udid` (client-chosen)
- Lists page via `lastTime`/`lastTimestamp` (unix seconds): `Long.MAX_VALUE` first, then the last item's timestamp; 10 per page; timestamps must be sent as integers (floats get HTTP 400)
- Images (Qiniu CDN): user photos need `?imageMogr2/auto-orient` (bare URLs are WAF-blocked); beer thumbnails use a `bg-` prefix; beer originals use a `-lg2` suffix
- Ratings: `r1=aroma r2=taste r3=look r4=feel rating=overall` (cross-validated against the website)
- Key endpoints: `user/id`, `comment/v3/user`, `comment/bar/user`, `beer/v3/{id}`, `beer/brewery/{id}`, `bar/{id}`, `follow/followInfo` (public), `follow/user/follower|following` (token), `signin` (may or may not work)

### Disclaimer

For exporting your own data for personal backup or migration. Not affiliated with jiuhuar; trademarks belong to their owners. Keep request rates gentle (built-in limits); the service may go offline permanently at any time.
