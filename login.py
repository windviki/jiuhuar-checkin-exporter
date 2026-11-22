# -*- coding: utf-8 -*-
"""OPTIONAL / EXPERIMENTAL: try to mint an auth token with account+password.

Why: follower/following name lists (follow/user/*) require a valid
``x-auth-token`` from any logged-in account. Counts work without login.

Reality check (2026): the platform has ended consumer operation. Login on
Android is broken and the website removed user login; the auth backend still
answers (``POST signin`` responds with proper error codes) but there is NO
guarantee it still validates old passwords, and the SMS gateway is dead.
Reportedly the iOS client could still log in recently — if you have a logged-in
iOS device, extracting its token is another (manual) route.

This helper never throws on auth failure; it prints the outcome and exits
with a non-zero code. On success the token is printed and saved to token.txt
for use as:  python main.py --nickname X --token $(cat token.txt)

Usage:
    python login.py --username 13500000000 --password 'your-password'
"""
import argparse
import sys

from jiuhuar_client import API_BASE, random_udid
from curl_cffi import requests
from Crypto.Cipher import AES
from base64 import b64decode
import json
import warnings

warnings.filterwarnings("ignore")

ERROR_HINTS = {
    "40004": "wrong username/password (or account not found)",
    "40017": "bad request format",
    "41001": "auth token problem",
    "429": "rate limited — wait a while",
}


def main():
    ap = argparse.ArgumentParser(description="experimental jiuhuar login")
    ap.add_argument("--username", required=True, help="account phone number")
    ap.add_argument("--password", required=True)
    ap.add_argument("--save", default="token.txt")
    args = ap.parse_args()

    udid = random_udid()
    key = udid.encode()[:16].ljust(16, b"0")
    headers = {
        "content-type": "application/json;charset=UTF-8",
        "platform": "Android", "model": "Pixel 4", "clientVersion": "5.8.8",
        "x-auth-token": "", "udid": udid, "language": "zh",
        "user-agent": "okhttp/3.12.0",
    }
    try:
        r = requests.post(API_BASE + "signin",
                          json={"username": args.username,
                                "password": args.password},
                          headers=headers, verify=False, timeout=20)
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] network error: {e}")
        sys.exit(2)

    if r.status_code != 200:
        print(f"[FAIL] HTTP {r.status_code} — auth backend unreachable")
        sys.exit(2)
    try:
        body = r.json()
    except Exception:  # noqa: BLE001
        print(f"[FAIL] unexpected response: {r.text[:120]}")
        sys.exit(2)

    code = body.get("code")
    if code != 0:
        hint = ERROR_HINTS.get(str(code), "")
        print(f"[FAIL] login rejected, code={code} msg={body.get('msg')!r} {hint}")
        print("The auth backend is alive but refused these credentials.")
        sys.exit(1)

    data = body.get("data")
    try:
        if body.get("crypted") and isinstance(data, str):
            pt = AES.new(key, AES.MODE_ECB).decrypt(b64decode(data))
            data = json.loads(pt[:-pt[-1]].decode("utf-8"))
        token = (data or {}).get("token")
    except Exception as e:  # noqa: BLE001
        print(f"[FAIL] could not decrypt login response: {e}")
        sys.exit(2)

    if not token:
        print(f"[FAIL] login answered but contained no token: {str(data)[:200]}")
        sys.exit(2)

    with open(args.save, "w", encoding="utf-8") as f:
        f.write(token)
    print(f"[OK] token acquired and saved to {args.save}")
    print(f"     use: python main.py --nickname NICK --token $(cat {args.save})")


if __name__ == "__main__":
    main()
