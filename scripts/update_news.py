#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ステーブルコイン関連ニュースを複数のRSSフィードから取得し、
キーワードで絞り込んで news.json（最新）と archive.json（全件累積）を更新する。
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

# 重要ニュースの自動判定キーワード（規制・制度・市場の節目など）
IMPORTANT_KEYWORDS = [
    "規制", "法案", "成立", "施行", "genius", "mica", "金融庁", "sec",
    "過去最高", "最高値", "破綻", "ディペッグ", "depeg", "禁止", "認可",
    "ライセンス", "license", "jpyc", "launch", "ban", "approval", "上場",
]

MAX_ITEMS = 6          # news.json に載せる最新件数
ARCHIVE_CAP = 1000     # archive.json の最大保持件数
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


def is_important(text):
    low = text.lower()
    return any(k.lower() in low for k in IMPORTANT_KEYWORDS)


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
    items.sort(key=lambda x: (0 if x["lang"] == "ja" else 1, -x["_sort"]))
    for it in items:
        it.pop("_sort", None)
        it.pop("lang", None)
    return items


def _key(it):
    return (it.get("url") or "").strip() or (it.get("title") or "")[:40]


def update_archive(here, news_items):
    """新たに出てきたニュースを archive.json に追記（全件累積）。
    既存エントリ（重要フラグ含む）は保持し、新規のみ追加する。"""
    arch_path = os.path.join(here, "archive.json")
    archive = []
    if os.path.exists(arch_path):
        try:
            with open(arch_path, encoding="utf-8") as f:
                archive = json.load(f).get("items", [])
        except Exception:
            archive = []

    seen = {_key(it) for it in archive}
    added = 0
    for it in news_items:
        k = _key(it)
        if not k or k in seen:
            continue
        archive.append({
            "date": it.get("date", ""),
            "title": it.get("title", ""),
            "summary": it.get("summary", ""),
            "url": it.get("url", ""),
            "important": is_important(f"{it.get('title','')} {it.get('summary','')}"),
        })
        seen.add(k)
        added += 1

    # 新しい順に並べ替え、上限でカット
    archive.sort(key=lambda x: x.get("date", ""), reverse=True)
    archive = archive[:ARCHIVE_CAP]

    if added or not os.path.exists(arch_path):
        with open(arch_path, "w", encoding="utf-8") as f:
            json.dump(
                {"updated": datetime.now(JST).isoformat(timespec="seconds"), "items": archive},
                f, ensure_ascii=False, indent=2,
            )
            f.write("\n")
        print(f"Archive: added {added} new item(s) (total {len(archive)})")
    else:
        print("Archive: no new items.")
    return added


def main():
    here = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    out_path = os.path.join(here, "news.json")

    items = collect()
    if not items:
        print("No matching news found — keeping existing files unchanged.")
        return 0

    update_archive(here, items)

    latest = items[:MAX_ITEMS]
    payload = {
        "updated": datetime.now(JST).isoformat(timespec="seconds"),
        "items": latest,
    }

    old_items = None
    if os.path.exists(out_path):
        try:
            with open(out_path, encoding="utf-8") as f:
                old_items = json.load(f).get("items")
        except Exception:
            pass
    if old_items == latest:
        print("News unchanged — news.json not rewritten.")
        return 0

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(f"Wrote {len(latest)} items to news.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
