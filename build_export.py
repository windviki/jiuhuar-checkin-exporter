# -*- coding: utf-8 -*-
"""Merge crawled data into final deliverables: JSON + CSV + HTML gallery.

Reads from the output directory produced by main.py:
    checkins_beer.json, checkins_bar.json, user_profile.json,
    beer_details.json, breweries.json
Writes:
    <nickname>_checkins_full.json   normalized full data
    <nickname>_checkins.csv         spreadsheet-friendly (Excel BOM)
    index.html                      dark-theme gallery (untappd-style)

Rating fields (validated against the website): r1=香气(aroma) r2=味道(taste)
r3=外观(look) r4=感受(feel), rating=总体(overall).
"""
import csv
import html
import json
import os
from datetime import datetime

API_URL = "https://napi.jiuhuar.com/api/"
FILE_HOST = "https://file1.jiuhuar.com"

RATING_KEYS = [("r1", "香气"), ("r2", "味道"), ("r3", "外观"), ("r4", "感受")]


def _exists(root, rel):
    return rel if rel and os.path.exists(os.path.join(root, rel)) else None


def _split_full_name(fn):
    """jiuhuar full names look like '中文|-|English' -> (cn, en)."""
    if not fn:
        return None, None
    if "|-|" in fn:
        cn, en = fn.split("|-|", 1)
        return cn.strip(), en.strip()
    return fn.strip(), None


def _stars(score):
    if not score:
        return ""
    return "★" * int(score) + ("½" if score - int(score) >= 0.25 else "")


def build(out_dir, nickname=None):
    def load(name, default):
        p = os.path.join(out_dir, name)
        return json.load(open(p, encoding="utf-8")) if os.path.exists(p) else default

    beer = load("checkins_beer.json", [])
    bar = load("checkins_bar.json", [])
    prof = load("user_profile.json", {})
    details = load("beer_details.json", {})
    breweries = load("breweries.json", {})
    bars = load("bars.json", {})
    img_root = os.path.join(out_dir, "images")
    nickname = nickname or prof.get("nickname") or "jiuhuar_user"

    def beer_block(raw):
        if not raw or not raw.get("oid"):
            return None
        oid = raw["oid"]
        d = details.get(oid) or {}
        name_cn, name_en = _split_full_name(d.get("fullName") or raw.get("name"))
        brw = d.get("brewery") or {}
        brw_d = breweries.get(brw.get("oid")) or {}
        br_cn, br_en = _split_full_name(brw_d.get("fullName") or brw.get("name"))
        style = d.get("style") or {}
        return {
            "id": oid, "name_cn": name_cn, "name_en": name_en,
            "brewery": {"id": brw.get("oid"), "name_cn": br_cn, "name_en": br_en,
                        "desc": brw_d.get("desc")} if (br_cn or brw.get("oid")) else None,
            "style": {"id": style.get("oid"), "name": style.get("name")}
                     if style.get("name") else None,
            "country": (d.get("country") or {}).get("name"),
            "abv": d.get("abv"), "ibu": d.get("ibu"), "desc": d.get("desc"),
            "type": raw.get("type") or d.get("type"),
            "pic_large": _exists(img_root, f"beers_lg/{oid}.png"),
            "pic_thumb": _exists(img_root, f"beers/{oid}.jpg"),
            "pic_url": f"{FILE_HOST}/bg-{raw['mainPic']}" if raw.get("mainPic") else None,
            "site_rating": d.get("rating"), "site_rating_cnt": d.get("rateCnt"),
        }

    def _bar_block(raw):
        if not raw or not raw.get("oid"):
            return None
        oid = raw["oid"]
        d = bars.get(oid) or {}
        city = " · ".join(x["name"] for x in
                          (d.get("province"), d.get("city"), d.get("district"))
                          if x and x.get("name"))
        return {
            "id": oid,
            "name": raw.get("name") or d.get("name"),
            "city": city or None,
            "address": d.get("address"),
            "open_time": d.get("openTime"),
            "tel": d.get("tel"),
            "rating": d.get("rating"),
            "desc": d.get("desc") or None,
            "logo_file": _exists(img_root, f"bars/{oid}.jpg"),
        }

    def norm(c, kind):
        images = []
        for i, im in enumerate(c.get("images") or []):
            uuid = im.split("|")[0]
            images.append({
                "file": _exists(img_root, f"checkins/{c['oid']}_{i}.jpg"),
                "url": f"{FILE_HOST}/{uuid}",
                "orig_size": "|".join(im.split("|")[1:]) or None,
            })
        ratings = {cn: c.get(rk) for rk, cn in RATING_KEYS} if kind == "beer" else {}
        ratings["总体"] = c.get("rating")
        return {
            "id": c["oid"],
            "type": "beer_checkin" if kind == "beer" else "bar_checkin",
            "datetime": datetime.fromtimestamp(c["createTime"]).strftime("%Y-%m-%d %H:%M"),
            "timestamp": c["createTime"],
            "beer": beer_block(c.get("beer")) if kind == "beer" else None,
            "bar": _bar_block(c.get("bar")) if (c.get("bar") or {}).get("oid") else None,
            "ratings": ratings,
            "stars": _stars(c.get("rating")),
            "content": c.get("content") or "",
            "tags": [t.get("name") for t in (c.get("commentTags") or [])],
            "images": images,
            "likes": c.get("praiseCnt", 0),
            "comments": c.get("replyCnt", 0),
            "web_url": f"https://www.jiuhuar.com/craftbeer/{c['beer']['oid']}.html"
                       if kind == "beer" and c.get("beer") else None,
        }

    items = [norm(c, "beer") for c in beer] + [norm(c, "bar") for c in bar]
    items.sort(key=lambda x: x["timestamp"], reverse=True)

    stats = {
        "total": len(items), "beer_checkins": len(beer), "bar_checkins": len(bar),
        "first": items[-1]["datetime"] if items else None,
        "last": items[0]["datetime"] if items else None,
        "images_total": sum(len(i["images"]) for i in items),
        "images_downloaded": sum(1 for i in items for im in i["images"] if im["file"]),
        "with_comment": sum(1 for i in items if i["content"]),
        "unique_beers": len({i["beer"]["id"] for i in items if i["beer"]}),
    }
    follow_info = load("follow_info.json", {})
    followers_raw = load("followers.json", [])
    following_raw = load("following.json", [])

    def _peeps(rows):
        return [{"id": u.get("oid"), "nickname": u.get("nickname"),
                 "signature": u.get("signature"),
                 "avatar_file": _exists(img_root, f"avatars/{u.get('oid')}.jpg"),
                 "followed_at": datetime.fromtimestamp(u["timestamp"]).strftime(
                     "%Y-%m-%d %H:%M") if u.get("timestamp") else None}
                for u in rows if u.get("oid")]

    doc = {"user": {"id": prof.get("oid"), "nickname": prof.get("nickname"),
                    "signature": prof.get("signature"),
                    "followers_count": follow_info.get("follower"),
                    "following_count": follow_info.get("following"),
                    "followers": _peeps(followers_raw) or None,
                    "following": _peeps(following_raw) or None,
                    # own avatar may be stored under avatars/{uid}.jpg because
                    # check-in author avatars register that path first
                    "avatar_file": (_exists(img_root, "profile/avatar.jpg")
                                    or _exists(img_root,
                                               f"avatars/{prof.get('oid')}.jpg")),
                    "background_file": _exists(img_root, "profile/background.jpg")},
           "stats": stats, "checkins": items}
    with open(os.path.join(out_dir, f"{nickname}_checkins_full.json"), "w",
              encoding="utf-8") as f:
        json.dump(doc, f, ensure_ascii=False, indent=1)

    # ---- CSV ----
    with open(os.path.join(out_dir, f"{nickname}_checkins.csv"), "w",
              encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["时间", "类型", "酒款(中)", "酒款(英)", "酒厂(中)", "酒厂(英)",
                    "国家", "风格", "ABV", "酒吧", "酒吧城市", "酒吧地址",
                    "香气", "味道", "外观", "感受", "总体评分",
                    "评论内容", "标签", "图片数", "图片文件", "点赞", "回复", "ID"])
        for i in items:
            b = i["beer"] or {}
            brw = b.get("brewery") or {}
            bar_i = i["bar"] or {}
            w.writerow([
                i["datetime"],
                "酒吧点评" if i["type"] == "bar_checkin" else "酒款点评",
                b.get("name_cn", ""), b.get("name_en", ""),
                brw.get("name_cn", ""), brw.get("name_en", ""),
                b.get("country", ""), (b.get("style") or {}).get("name", ""),
                b.get("abv", ""),
                bar_i.get("name", ""), bar_i.get("city", ""), bar_i.get("address", ""),
                i["ratings"].get("香气", ""), i["ratings"].get("味道", ""),
                i["ratings"].get("外观", ""), i["ratings"].get("感受", ""),
                i["ratings"].get("总体", ""),
                i["content"], "、".join(i["tags"]), len(i["images"]),
                " | ".join(im["file"] or ("MISSING:" + im["url"]) for im in i["images"]),
                i["likes"], i["comments"], i["id"],
            ])

    # ---- HTML gallery ----
    def card(i):
        b = i["beer"] or {}
        brw = b.get("brewery") or {}
        title = b.get("name_en") or b.get("name_cn") or (i["bar"] or {}).get("name") or ""
        photos = [im["file"] for im in i["images"] if im["file"]]
        if photos:
            cover = f'<img src="images/{photos[0]}" loading="lazy" alt="">'
        elif b.get("pic_large"):
            cover = f'<img src="images/{b["pic_large"]}" loading="lazy" alt="">'
        elif (i["bar"] or {}).get("logo_file"):
            cover = f'<img src="images/{i["bar"]["logo_file"]}" loading="lazy" alt="">'
        else:
            cover = '<div class="nophoto">🍺</div>'
        sub = " · ".join(x for x in [brw.get("name_en") or brw.get("name_cn"),
                                     (b.get("style") or {}).get("name"),
                                     f'{b["abv"]}%' if b.get("abv") else None] if x)
        sub_cn = (f'<div class="sub cn">{html.escape(b["name_cn"] or "")}</div>'
                  if b.get("name_en") and b.get("name_cn") else "")
        venue = ""
        if i["bar"]:
            venue = f' · 📍 {html.escape(i["bar"]["name"])}'
            if i["bar"].get("city"):
                venue += f'（{html.escape(i["bar"]["city"])}）'
        dims = " ".join(f'<span>{k}{v:g}</span>' for k, v in i["ratings"].items()
                        if v is not None and k != "总体")
        dims = f'<div class="dims">{dims}</div>' if dims else ""
        tags = "".join(f'<span class="tag">{html.escape(t)}</span>' for t in i["tags"])
        tags = f'<div class="tags">{tags}</div>' if tags else ""
        comment = (f'<p class="comment">{html.escape(i["content"])}</p>'
                   if i["content"] else "")
        return f"""
<article class="card">
  {cover}
  <div class="body">
    <div class="head"><span class="beer">{html.escape(title)}</span><span class="stars">{i["stars"]}</span></div>
    <div class="sub">{html.escape(sub)}</div>{sub_cn}
    <div class="time">🕐 {i["datetime"]}{venue}</div>
    {comment}{dims}{tags}
    <div class="meta">#{i['id'][:8]} · 👍 {i['likes']}{' · 📷 ' + str(len(photos)) + '张' if len(photos) > 1 else ''}</div>
  </div>
</article>"""

    cards = "".join(card(i) for i in items)

    # ---- social section: followers / following with avatars ----
    def ppl_chip(u, group):
        nick = u.get("nickname") or u.get("id", "")[:6]
        tip = nick + (f' · 关注于 {u["followed_at"][:10]}' if u.get("followed_at") else "")
        label = nick if len(nick) <= 6 else nick[:6] + "…"
        av = (f'<img src="images/{u["avatar_file"]}" loading="lazy" alt="">'
              if u.get("avatar_file")
              else f'<span class="noav">{html.escape(nick[:1].upper())}</span>')
        return (f'<span class="ppl" title="{html.escape(tip)}">{av}'
                f'<i>{html.escape(label)}</i></span>')

    def social_block():
        fol, fng = doc["user"].get("followers"), doc["user"].get("following")
        if not fol and not fng:
            return ""
        groups = ""
        for label, rows in (("关注", fng or []), ("粉丝", fol or [])):
            if rows:
                chips = "".join(ppl_chip(u, label) for u in rows)
                groups += (f'<div class="sgroup"><span class="glabel">{label} '
                           f'{len(rows)}</span><div class="peeps">{chips}</div></div>')
        if not groups:
            return ""
        return (f'<div class="social"><div class="shead">👥 关注与粉丝'
                f'（关注 {doc["user"].get("following_count", len(fng or []))} · '
                f'粉丝 {doc["user"].get("followers_count", len(fol or []))}）</div>'
                f'{groups}</div>')

    gallery = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8">
<title>酒花儿导出 · {html.escape(nickname)} · {stats['total']} 条 checkin</title>
<style>
  body {{ font-family: "Segoe UI", system-ui, sans-serif; margin: 0; background: #161320; color: #e8e6f0; }}
  h1 {{ padding: 20px 24px 4px; font-size: 20px; }}
  .summary {{ padding: 0 24px 16px; color: #9b96b0; font-size: 13px; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(270px, 1fr)); gap: 14px; padding: 0 16px 40px; }}
  .card {{ background: #201c2e; border-radius: 10px; overflow: hidden; }}
  .card img {{ width: 100%; aspect-ratio: 3/4; object-fit: cover; display: block; background: #0d0b14; }}
  .nophoto {{ width: 100%; aspect-ratio: 3/4; display: flex; align-items: center; justify-content: center; font-size: 48px; background: #0d0b14; }}
  .body {{ padding: 10px 12px 12px; }}
  .head {{ display: flex; justify-content: space-between; gap: 8px; }}
  .beer {{ font-weight: 600; }}
  .stars {{ color: #f5a623; white-space: nowrap; font-size: 12px; }}
  .sub {{ color: #9b96b0; font-size: 12px; margin-top: 2px; }}
  .sub.cn {{ color: #7d7896; }}
  .time {{ color: #7d7896; font-size: 12px; margin-top: 6px; }}
  .comment {{ font-size: 13px; margin: 6px 0 0; line-height: 1.5; }}
  .dims {{ margin-top: 6px; }}
  .dims span {{ font-size: 11px; color: #8a85a8; background: #2a2540; border-radius: 4px; padding: 1px 6px; margin-right: 4px; }}
  .tags {{ margin-top: 6px; }}
  .tag {{ font-size: 11px; color: #b39ddb; background: #2a2540; border-radius: 10px; padding: 1px 8px; margin-right: 4px; display: inline-block; }}
  .meta {{ color: #635e7d; font-size: 11px; margin-top: 8px; }}
  .social {{ padding: 4px 24px 18px; }}
  .shead {{ color: #9b96b0; font-size: 14px; margin: 6px 0 10px; }}
  .sgroup {{ margin-bottom: 10px; }}
  .glabel {{ color: #7d7896; font-size: 12px; display: block; margin-bottom: 6px; }}
  .peeps {{ display: flex; flex-wrap: wrap; gap: 8px; }}
  .ppl {{ display: inline-flex; align-items: center; gap: 6px; background: #201c2e; border-radius: 16px; padding: 3px 10px 3px 3px; font-size: 12px; color: #c9c5dd; }}
  .ppl img {{ width: 26px; height: 26px; border-radius: 50%; object-fit: cover; display: block; }}
  .noav {{ width: 26px; height: 26px; border-radius: 50%; background: #3a3355; color: #b39ddb; display: inline-flex; align-items: center; justify-content: center; font-size: 12px; font-style: normal; }}
  .ppl i {{ font-style: normal; max-width: 84px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
</style>
</head>
<body>
<h1>🍺 酒花儿数据导出 — {html.escape(nickname)}</h1>
<div class="summary">{stats['total']} 条 checkin · {stats['beer_checkins']} 酒款 + {stats['bar_checkins']} 酒吧 · {stats['unique_beers']} 款酒 · {stats['with_comment']} 条评论 · {stats['images_total']} 张图片 · {(stats['first'] or '')[:10]} ~ {(stats['last'] or '')[:10]}</div>
{social_block()}
<div class="grid">{cards}
</div>
</body>
</html>"""
    with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(gallery)

    return stats


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "./output"
    print(json.dumps(build(out), ensure_ascii=False, indent=1))
