# -*- coding: utf-8 -*-
"""Core client for the (now read-only) jiuhuar beer app API.

Protocol facts this client relies on, recovered so users can rescue their own
data before the service disappears (see README.md):

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


def try_login(username: str, password: str) -> str:
    """Exchange account+password for an auth token.

    Returns the token string on success; raises RuntimeError with a readable
    message otherwise. The password is used only for this one request.
    """
    udid = random_udid()
    headers = {
        "content-type": "application/json;charset=UTF-8",
        "platform": "Android", "model": "Pixel 4", "clientVersion": "5.8.8",
        "x-auth-token": "", "udid": udid, "language": "zh",
        "user-agent": "okhttp/3.12.0",
    }
    r = requests.post(API_BASE + "signin",
                      json={"username": username, "password": password},
                      headers=headers, verify=False, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"auth backend unreachable (HTTP {r.status_code})")
    try:
        body = r.json()
    except Exception:  # noqa: BLE001
        raise RuntimeError(f"unexpected response: {r.text[:120]}") from None
    if body.get("code") != 0:
        hints = {"40004": "wrong username/password", "429": "rate limited, retry later"}
        raise RuntimeError("login rejected, code=%s msg=%r %s" % (
            body.get("code"), body.get("msg"), hints.get(str(body.get("code")), "")))
    data = body.get("data")
    try:
        if body.get("crypted") and isinstance(data, str):
            key = udid.encode()[:16].ljust(16, b"0")
            pt = AES.new(key, AES.MODE_ECB).decrypt(b64decode(data))
            data = json.loads(pt[:-pt[-1]].decode("utf-8"))
        token = (data or {}).get("token")
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"could not decrypt login response: {e}") from None
    if not token:
        raise RuntimeError("login answered but contained no token")
    return token


def image_url(uuid: str) -> str:
    """Original-resolution URL for a user-content image uuid."""
    return f"{FILE_HOST}/{uuid}?imageMogr2/auto-orient"


def beer_thumb_url(main_pic: str) -> str:
    return f"{FILE_HOST}/bg-{main_pic}"


def beer_large_url(main_pic: str) -> str:
    return f"{S1_HOST}/{main_pic}-lg2"


class JiuhuarClient:
    def __init__(self, udid: str | None = None, token: str | None = None,
                 client_version: str = "5.8.8"):
        self.udid = udid or random_udid()
        self.key = self.udid.encode()[:16].ljust(16, b"0")
        self.session = requests.Session()
        self.headers = {
            "content-type": "application/json;charset=UTF-8",
            "platform": "Android",
            "model": "Pixel 4",
            "clientVersion": client_version,
            "x-auth-token": token or "",
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
            last_time = int(min(times))  # guard against float serialization
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

    # -- social graph --------------------------------------------------------

    def follow_counts(self, uid: str) -> dict:
        """Public: {'follower': N, 'following': M}."""
        return self.get("follow/followInfo", {"uid": uid}) or {}

    def _follow_page(self, path: str, uid: str, last_ts: int) -> list:
        return self.get(path, {"uid": uid, "lastTimestamp": last_ts}) or []

    def _follow_all(self, path: str, uid: str, delay: float = 0.3) -> list:
        """Requires a valid x-auth-token (any logged-in account)."""
        items, seen, last_ts = [], set(), LONG_MAX
        while True:
            batch = self._follow_page(path, uid, last_ts)
            if not isinstance(batch, list) or not batch:
                break
            for u in batch:
                if u.get("oid") and u["oid"] not in seen:
                    seen.add(u["oid"])
                    items.append(u)
            # decrypted JSON may carry timestamps as floats (1.67e9); the
            # server rejects "1675609168.0" as a long -> cast to int
            times = [u.get("timestamp") for u in batch if u.get("timestamp")]
            if len(batch) < 10 or not times:
                break
            last_ts = int(min(times))
            time.sleep(delay)
        return items

    def followers(self, uid: str) -> list:
        return self._follow_all("follow/user/follower", uid)

    def following(self, uid: str) -> list:
        return self._follow_all("follow/user/following", uid)
