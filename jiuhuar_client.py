# -*- coding: utf-8 -*-
"""Core client for the (now read-only) jiuhuar beer app API.

Reverse-engineered facts this client relies on (see README.md):

* API base:  https://napi.jiuhuar.com/api/
* The server's TLS certificate expired in 2020 but the service still serves
  data -> certificate verification must be disabled.
* Every request must look like the Android app; the decisive headers are
  ``content-type`` (JSON vs XML response format) and ``udid``.
* Responses: {"code":0,"crypted":true,"data":"<base64>"} where the payload is
  AES-128/ECB/PKCS7 encrypted with **the udid header value** as the key
  (padded/truncated to 16 bytes). The key is therefore client-chosen.
* List endpoints page by ``lastTime`` (unix seconds): first page uses
  Long.MAX_VALUE, later pages the ``createTime`` of the last received item.
  Page size is 10; a shorter page means the end.
* Images live on Qiniu CDNs:
    - user content (uuid keys):   https://file1.jiuhuar.com/{uuid}?imageMogr2/auto-orient
      (the imageMogr2 query is mandatory, plain URLs are blocked by the WAF)
    - beer thumbnails:            https://file1.jiuhuar.com/bg-{mainPic}
    - beer original resolution:   https://s1.jiuhuar.com/{mainPic}-lg2  (or -lg webp)
"""
import json
import random
import string
import time
from base64 import b64decode

from curl_cffi import requests
from Crypto.Cipher import AES

# NOTE: keep the plain curl_cffi Session below. A browser-impersonated session
# (impersonate="chrome") changes the TLS/HTTP2 fingerprint and the WAF then
# answers with XML instead of JSON, breaking _decrypt. Plain requests +
# app-shaped headers is what the real app looks like.

API_BASE = "https://napi.jiuhuar.com/api/"
FILE_HOST = "https://file1.jiuhuar.com"
S1_HOST = "https://s1.jiuhuar.com"
LONG_MAX = 9223372036854775807
PAGE_SIZE = 10


def random_udid(length: int = 16) -> str:
    return "".join(random.choices(string.ascii_lowercase + string.digits, k=length))


def image_url(uuid: str) -> str:
    """Original-resolution URL for a user-content image uuid."""
    return f"{FILE_HOST}/{uuid}?imageMogr2/auto-orient"


def beer_thumb_url(main_pic: str) -> str:
    return f"{FILE_HOST}/bg-{main_pic}"


def beer_large_url(main_pic: str) -> str:
    return f"{S1_HOST}/{main_pic}-lg2"


class JiuhuarClient:
    def __init__(self, udid: str | None = None, client_version: str = "5.8.8"):
        self.udid = udid or random_udid()
        self.key = self.udid.encode()[:16].ljust(16, b"0")
        self.session = requests.Session()
        self.headers = {
            "content-type": "application/json;charset=UTF-8",
            "platform": "Android",
            "model": "Pixel 4",
            "clientVersion": client_version,
            "x-auth-token": "",
            "udid": self.udid,
            "language": "zh",
            "user-agent": "okhttp/3.12.0",
        }

    # -- transport ---------------------------------------------------------

    def _decrypt(self, payload: str):
        ct = b64decode(payload)
        pt = AES.new(self.key, AES.MODE_ECB).decrypt(ct)
        pad = pt[-1]
        if not 1 <= pad <= 16:
            raise ValueError("bad AES padding (wrong key?)")
        return json.loads(pt[:-pad].decode("utf-8"))

    def get(self, path: str, params: dict | None = None, retries: int = 4):
        url = path if path.startswith("http") else API_BASE + path
        last_err = None
        for attempt in range(retries):
            try:
                r = self.session.get(url, params=params, headers=self.headers,
                                     verify=False, timeout=25)
                if r.status_code != 200:
                    raise RuntimeError(f"HTTP {r.status_code}")
                obj = r.json()
                if obj.get("code") != 0:
                    raise RuntimeError(f"API code={obj.get('code')} msg={obj.get('msg')}")
                if obj.get("crypted"):
                    return self._decrypt(obj["data"])
                return obj.get("data")
            except Exception as e:  # noqa: BLE001 - retry any transport error
                last_err = e
                time.sleep(1.5 * (attempt + 1))
        raise RuntimeError(f"GET {path} failed after {retries} tries: {last_err}")

    # -- endpoints ---------------------------------------------------------

    def user_id(self, nickname: str) -> str:
        uid = self.get("user/id", {"nickname": nickname})
        if not isinstance(uid, str) or len(uid) < 8:
            raise RuntimeError(f"nickname {nickname!r} not found (got: {uid!r})")
        return uid

    def user_profile(self, uid: str) -> dict:
        return self.get("user/v2/he", {"uid": uid}) or {}

    def user_comment_cnt(self, uid: str) -> dict:
        return self.get(f"user/comment/cnt/{uid}") or {}

    def crawl_list(self, path: str, extra: dict | None = None,
                   delay: float = 0.3) -> list:
        """Page through a lastTime-desc list endpoint until exhausted."""
        items, seen, last_time = [], set(), LONG_MAX
        extra = extra or {}
        while True:
            batch = self.get(path, {**extra, "lastTime": last_time})
            if not isinstance(batch, list) or not batch:
                break
            for it in batch:
                k = it.get("oid")
                if not k or k not in seen:
                    if k:
                        seen.add(k)
                    items.append(it)
            if len(batch) < PAGE_SIZE:
                break
            times = [it.get("createTime") for it in batch if it.get("createTime")]
            if not times:
                break
            last_time = min(times)
            time.sleep(delay)
        return items

    def beer_checkins(self, uid: str) -> list:
        return self.crawl_list("comment/v3/user", {"uid": uid})

    def bar_checkins(self, uid: str) -> list:
        return self.crawl_list("comment/bar/user", {"uid": uid})

    def beer_detail(self, beer_id: str) -> dict:
        return self.get(f"beer/v3/{beer_id}",
                        {"longitude": 0.0, "latitude": 0.0}) or {}

    def brewery_detail(self, brewery_id: str) -> dict:
        return self.get(f"beer/brewery/{brewery_id}") or {}

    def bar_detail(self, bar_id: str) -> dict:
        """Returns the inner 'bar' object of GET bar/{id}."""
        d = self.get(f"bar/{bar_id}") or {}
        return d.get("bar") or {}
