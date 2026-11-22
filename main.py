# -*- coding: utf-8 -*-
"""Export ALL of your jiuhuar (酒花儿) check-ins: ratings, comments, photos.

The app has stopped serving users and login no longer works, but the API
still serves public data without authentication, which is enough to export
your own history (your profile is public unless you hid it).

Usage:
    python main.py --nickname YOUR_NICKNAME            # full run -> ./output
    python main.py --uid 5xxxxxxxxxxxxxxxxxxxxxx       # if you know your uid
    python main.py --nickname YOUR_NICKNAME --skip-images --skip-enrich
"""
import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from jiuhuar_client import (JiuhuarClient, beer_large_url, beer_thumb_url,
                            image_url)

steps_log = []


def log(msg):
    print(msg, flush=True)
    steps_log.append(msg)


def out_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)


def step_crawl(client, uid, out):
    cnt = client.user_comment_cnt(uid)
    log(f"server-side counts: {json.dumps(cnt, ensure_ascii=False)}")
    beer = client.beer_checkins(uid)
    bar = client.bar_checkins(uid)
    log(f"crawled {len(beer)} beer check-ins + {len(bar)} bar check-ins "
        f"(expected {cnt.get('beerCommentCnt')}/{cnt.get('barCommentCnt')})")
    out_json(os.path.join(out, "checkins_beer.json"), beer)
    out_json(os.path.join(out, "checkins_bar.json"), bar)
    return beer, bar


def step_enrich(client, beer_checkins, bar_checkins, out):
    uniq = {}
    for c in beer_checkins:
        b = c.get("beer") or {}
        if b.get("oid"):
            uniq[b["oid"]] = b.get("name")
    log(f"fetching details for {len(uniq)} unique beers ...")
    details = {}
    for n, oid in enumerate(uniq, 1):
        try:
            details[oid] = client.beer_detail(oid)
        except Exception as e:  # noqa: BLE001
            log(f"  beer detail failed {oid}: {e}")
        if n % 100 == 0:
            log(f"  {n}/{len(uniq)}")
        time.sleep(0.25)
    out_json(os.path.join(out, "beer_details.json"), details)

    seen, breweries = set(), {}
    for d in details.values():
        bw = (d or {}).get("brewery") or {}
        if bw.get("oid") and bw["oid"] not in seen:
            seen.add(bw["oid"])
            try:
                breweries[bw["oid"]] = client.brewery_detail(bw["oid"])
            except Exception as e:  # noqa: BLE001
                log(f"  brewery failed {bw['oid']}: {e}")
            time.sleep(0.25)
    log(f"fetched {len(breweries)} breweries")
    out_json(os.path.join(out, "breweries.json"), breweries)

    # bar details (city/address/opening hours/pictures) for bar check-ins
    seen_bars, bars = set(), {}
    for c in bar_checkins:
        b = c.get("bar") or {}
        if b.get("oid") and b["oid"] not in seen_bars:
            seen_bars.add(b["oid"])
            try:
                bars[b["oid"]] = client.bar_detail(b["oid"])
            except Exception as e:  # noqa: BLE001
                log(f"  bar failed {b['oid']}: {e}")
            time.sleep(0.25)
    log(f"fetched {len(bars)} bars")
    out_json(os.path.join(out, "bars.json"), bars)
    return details, breweries, bars


def step_images(client, beer_checkins, bar_checkins, details, bars, profile, out):
    img_root = os.path.join(out, "images")
    tasks = {}  # url -> relative path

    def add(url, rel):
        if url:
            tasks.setdefault(url, rel)

    for c in beer_checkins + bar_checkins:
        # check-in photos
        for i, im in enumerate(c.get("images") or []):
            add(image_url(im.split("|")[0]), f"checkins/{c['oid']}_{i}.jpg")
        # avatars of comment authors
        author = c.get("author") or {}
        if author.get("avatar"):
            add(image_url(author["avatar"].split("|")[0]),
                f"avatars/{author.get('oid', 'unknown')}.jpg")
        # bar logo from the check-in payload
        bar = c.get("bar") or {}
        if bar.get("logo"):
            add(image_url(bar["logo"]), f"bars/{bar.get('oid', 'unknown')}.jpg")
        # beer thumbs straight from the check-in data (works with --skip-enrich)
        b = c.get("beer") or {}
        if b.get("mainPic"):
            add(beer_thumb_url(b["mainPic"]), f"beers/{b['oid']}.jpg")

    # beer originals at native resolution + thumbs from the details crawl
    for oid, d in (details or {}).items():
        mp = (d or {}).get("mainPic")
        if mp:
            add(beer_large_url(mp), f"beers_lg/{oid}.png")
            add(beer_thumb_url(mp), f"beers/{oid}.jpg")

    # bar cover: prefer the logo, else the first bar photo (both uuid|w|h or F-keys)
    for oid, b in (bars or {}).items():
        if b.get("logo"):
            add(image_url(b["logo"].split("|")[0]), f"bars/{oid}.jpg")
        elif b.get("images"):
            add(image_url(b["images"][0].split("|")[0]), f"bars/{oid}.jpg")

    # profile avatar / background
    if profile.get("avatar"):
        add(image_url(profile["avatar"].split("|")[0]), "profile/avatar.jpg")
    if profile.get("background"):
        add(image_url(profile["background"].split("|")[0]),
            "profile/background.jpg")

    for sub in ("checkins", "beers", "beers_lg", "avatars", "bars", "profile"):
        os.makedirs(os.path.join(img_root, sub), exist_ok=True)

    todo = [(u, r) for u, r in tasks.items()
            if not os.path.exists(os.path.join(img_root, r))]
    log(f"downloading {len(todo)} images ...")
    fails = []

    def fetch(url, path):
        last = None
        for attempt in range(3):
            try:
                r = client.session.get(url, timeout=30, verify=False,
                                       headers={"user-agent": "okhttp/3.12.0",
                                                "referer": "https://www.jiuhuar.com/"})
                if r.status_code == 200 and len(r.content) > 200:
                    with open(path, "wb") as f:
                        f.write(r.content)
                    return None
                last = f"HTTP {r.status_code}"
            except Exception as e:  # noqa: BLE001
                last = str(e)
                time.sleep(1 + attempt)
        return last

    def dl(item):
        url, rel = item
        path = os.path.join(img_root, rel)
        err = fetch(url, path)
        if err and "-lg2" in url:  # original PNG missing -> same-size webp
            err = fetch(url.replace("-lg2", "-lg"), path)
        return url if err else None

    with ThreadPoolExecutor(max_workers=6) as ex:
        for n, res in enumerate(ex.map(dl, todo), 1):
            if res:
                fails.append(res)
            if n % 200 == 0:
                log(f"  {n}/{len(todo)}")
    log(f"images done, {len(fails)} failed")
    if fails:
        out_json(os.path.join(out, "image_failures.json"), fails)


def main():
    ap = argparse.ArgumentParser(description="jiuhuar check-in exporter")
    ap.add_argument("--nickname", help="your nick name on jiuhuar")
    ap.add_argument("--uid", help="your user id (overrides nickname)")
    ap.add_argument("--out", default="./output", help="output directory")
    ap.add_argument("--skip-enrich", action="store_true",
                    help="skip beer/brewery detail crawl")
    ap.add_argument("--skip-images", action="store_true", help="skip image download")
    args = ap.parse_args()

    if not args.nickname and not args.uid:
        ap.error("need --nickname or --uid")

    os.makedirs(args.out, exist_ok=True)
    client = JiuhuarClient()
    log(f"udid (also the AES key): {client.udid}")

    uid = args.uid or client.user_id(args.nickname)
    profile = client.user_profile(uid)
    nickname = profile.get("nickname") or args.nickname or uid
    log(f"uid={uid} nickname={nickname}")
    out_json(os.path.join(args.out, "user_profile.json"), profile)

    beer, bar = step_crawl(client, uid, args.out)

    details, bars = None, None
    if not args.skip_enrich:
        details, breweries, bars = step_enrich(client, beer, bar, args.out)

    if not args.skip_images:
        step_images(client, beer, bar, details, bars, profile, args.out)

    # build final deliverables with the separate builder
    import build_export
    build_export.build(args.out, nickname)
    log("all done -> " + args.out)
    with open(os.path.join(args.out, "run_log.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(steps_log) + "\n")


if __name__ == "__main__":
    main()
