#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ステーブルコイン関連ニュースを複数のRSSフィードから取得し、
キーワードで絞り込んで news.json を更新するスクリプト。
GitHub Actions から毎日実行される。依存パッケージなし（標準ライブラリのみ）。
"""
import json
import re
import sys
import os
import html as htmllib
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET

JST = timezone(timedelta(hours=9))

# 日本語フィードを優先（見出しが日本語になる）。英語フィードは補助。
FEEDS = [
    ("ja", "https://coinpost.jp/?feed=rss2"),
    ("ja", "https://www.neweconomy.jp/feed"),
    ("en", "https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("en", "https://cointelegraph.com/rss"),
]

# このいずれかを含む記事だけを採用
KEYWORDS = [
    "ステーブルコイン", "ステーブル", "stablecoin", "stable coin",
    "usdt", "usdc", "jpyc", "pyusd", "tether", "usde", "rlusd",
    "genius act", "資金移動業", "円建て",
]

MAX_ITEMS = 6
TAG_RE = re.compile(r"<[^>]+>")
WS_RE = re.compile(r"\s+")


def clean(text):
    if not text:
        return ""
    text = TAG_RE.sub("", text)
    text = htmllib.unescape(text)
    text = WS_RE.sub(" ", text).strip()
    return text


def parse_date(s):
    if not s:
        return None
    s = s.strip()
    fmts = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S %Z",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
    ]
    for f in fmts:
        try:
            dt = datetime.strptime(s, f)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except ValueError:
            continue
    return None


def fetch(url):
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (stablecoin-site news bot)"})
    with urlopen(req, timeout=25) as r:
        return r.read()


def matches(text):
    low = text.lower()
    return any(k.lower() in low for k in KEYWORDS)


def collect():
    items = []
    seen_titles = set()
    for lang, url in FEEDS:
        try:
            raw = fetch(url)
            root = ET.fromstring(raw)
        except Exception as e:
            print(f"  skip {url}: {e}", file=sys.stderr)
            continue
        # RSS 2.0: channel/item ; Atom: entry
        nodes = root.iter("item")
        count = 0
        for it in nodes:
            title = clean(it.findtext("title"))
            desc = clean(it.findtext("description"))
            link = (it.findtext("link") or "").strip()
            pub = parse_date(it.findtext("pubDate"))
            blob = f"{title} {desc}"
            if not title or not matches(blob):
                continue
            key = title[:40]
            if key in seen_titles:
                continue
            seen_titles.add(key)
            items.append({
                "lang": lang,
                "date": pub.astimezone(JST).strftime("%Y-%m-%d") if pub else "",
                "_sort": pub.timestamp() if pub else 0,
                "title": title,
                "summary": (desc[:110] + "…") if len(desc) > 110 else desc,
                "url": link,
            })
            count += 1
        print(f"  {url}: {count} matched")
    # 日本語を優先しつつ新しい順
    items.sort(key=lambda x: (0 if x["lang"] == "ja" else 1, -x["_sort"]))
    for it in items:
        it.pop("_sort", None)
        it.pop("lang", None)
    return items[:MAX_ITEMS]


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = os.path.join(here, "news.json")

    items = collect()
    if not items:
        print("No matching news found — keeping existing news.json unchanged.")
        return 0

    payload = {
        "updated": datetime.now(JST).isoformat(timespec="seconds"),
        "items": items,
    }

    # 中身（updated以外）が変わっていなければ書き換えない
    old_items = None
    if os.path.exists(out_path):
        try:
            with open(out_path, encoding="utf-8") as f:
                old_items = json.load(f).get("items")
        except Exception:
            pass
    if old_items == items:
        print("News unchanged — no commit needed.")
        return 0

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"Wrote {len(items)} items to news.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
