#!/usr/bin/env python3
"""
Fetch news from multiple Chinese finance sources and export a merged JSON file.

Sources:
- 财联社 via akshare.news_cailianpress
- 新浪财经 via RSS
- 巨潮资讯 via akshare.stock_gsnews_latest
- 雪球 via pysnowball
"""
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List

import feedparser
import pandas as pd
import requests


def normalize_dt(value) -> str:
    """Convert assorted datetime formats to ISO8601 (UTC)."""
    if value is None:
        return datetime.now(timezone.utc).isoformat()
    if isinstance(value, pd.Timestamp):
        dt = value.to_pydatetime()
    elif isinstance(value, datetime):
        dt = value
    elif isinstance(value, (int, float)):
        ts = value / 1000.0 if value > 1_000_000_000_000 else value
        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
    elif isinstance(value, str):
        dt = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z"):
            try:
                dt = datetime.strptime(value, fmt)
                break
            except ValueError:
                continue
        if dt is None:
            try:
                dt = datetime.fromisoformat(value)
            except Exception:
                return datetime.now(timezone.utc).isoformat()
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone(timedelta(hours=8)))
    else:
        return datetime.now(timezone.utc).isoformat()
    return dt.astimezone(timezone.utc).isoformat()


def make_session() -> requests.Session:
    """Create a requests session; optional proxy via NEWS_PROXY or env proxies."""
    session = requests.Session()
    proxy = os.getenv("NEWS_PROXY")
    if proxy:
        session.proxies = {"http": proxy, "https": proxy}
        session.trust_env = False
    else:
        session.trust_env = True  # allow http_proxy/https_proxy if user exports
    return session


def fetch_cailian() -> List[Dict]:
    import akshare as ak

    # Prefer akshare API if available; otherwise fallback to CLS HTTP API.
    if hasattr(ak, "stock_news_cailianpress"):
        try:
            df = ak.stock_news_cailianpress()
            items = []
            for _, row in df.iterrows():
                title = row.get("title") or row.get("摘要") or row.get("content") or ""
                link = row.get("url") or row.get("链接") or row.get("source") or ""
                pub = row.get("time") or row.get("发布时间")
                items.append(
                    {
                        "source": "财联社",
                        "title_zh": str(title).strip(),
                        "link": str(link).strip(),
                        "pubDate": normalize_dt(pub),
                    }
                )
            if items:
                return items
        except Exception as exc:
            print(f"[cailian] fetch error akshare stock_news_cailianpress: {exc}")

    if hasattr(ak, "news_cailianpress"):
        try:
            df = ak.news_cailianpress()
        except Exception as exc:
            print(f"[cailian] fetch error akshare: {exc}")
            df = None
        if df is not None:
            items = []
            for _, row in df.iterrows():
                title = row.get("title") or row.get("摘要") or row.get("content") or ""
                link = row.get("url") or row.get("链接") or row.get("source") or ""
                pub = row.get("time") or row.get("发布时间")
                items.append(
                    {
                        "source": "财联社",
                        "title_zh": title.strip(),
                        "link": str(link).strip(),
                        "pubDate": normalize_dt(pub),
                    }
                )
            return items

    # Fallback: CLS API (disable env proxies)
    session = make_session()
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": "https://www.cls.cn/",
        "Accept": "application/json",
    }

    # Try telegraphList first
    urls = [
        ("telegraphList", {"app": "CailianpressWeb", "category": 0, "lastTime": 0}),
        ("rollList", {"app": "CailianpressWeb", "category": "1", "page": 1, "size": 40}),
    ]
    for path, params in urls:
        try:
            resp = session.get(f"https://www.cls.cn/nodeapi/{path}", params=params, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if path == "telegraphList":
                roll = data.get("data", {}).get("roll_data", [])
            else:
                roll = data.get("data", {}).get("roll_data", [])
            items = []
            for row in roll:
                title = row.get("title") or row.get("content") or ""
                link = f"https://www.cls.cn/detail/{row.get('id')}" if row.get("id") else ""
                pub = row.get("ctime") or row.get("time")
                items.append(
                    {
                        "source": "财联社",
                        "title_zh": str(title).strip(),
                        "link": str(link).strip(),
                        "pubDate": normalize_dt(pub),
                    }
                )
            if items:
                return items
        except Exception as exc:
            print(f"[cailian] fetch error {path}: {exc}")
            continue
    return []


def fetch_sina_rss() -> List[Dict]:
    rss_url = "https://rss.sina.com.cn/news/finance/bizfocus15.xml"
    try:
        feed = feedparser.parse(rss_url)
    except Exception as exc:
        print(f"[sina] fetch error: {exc}")
        return []
    items = []
    for entry in feed.entries:
        pub = entry.get("published") or entry.get("updated")
        items.append(
            {
                "source": "新浪财经",
                "title_zh": entry.get("title", "").strip(),
                "link": entry.get("link", "").strip(),
                "pubDate": normalize_dt(pub),
            }
        )
    return items


def fetch_juchao() -> List[Dict]:
    # Try akshare if future versions provide the API
    try:
        import akshare as ak

        if hasattr(ak, "stock_gsnews_latest"):
            df = ak.stock_gsnews_latest()
            items = []
            for _, row in df.iterrows():
                title = row.get("title") or row.get("标题") or ""
                link = row.get("url") or row.get("href") or ""
                pub = row.get("datetime") or row.get("发布时间")
                items.append(
                    {
                        "source": "巨潮资讯",
                        "title_zh": title.strip(),
                        "link": str(link).strip(),
                        "pubDate": normalize_dt(pub),
                    }
                )
            return items
    except Exception as exc:
        print(f"[juchao] fetch error akshare: {exc}")

    # Fallback: cninfo disclosure API (SH+SZ latest)
    def _fetch_plate(plate: str) -> List[Dict]:
        url = "https://www.cninfo.com.cn/new/disclosure/stock"
        payload = {
            "pageNum": 1,
            "pageSize": 30,
            "column": "szse" if plate == "szse" else "sse",
            "tabName": "fulltext",
            "plate": plate,
            "searchkey": "",
            "secid": "",
            "sortName": "",
            "sortType": "",
            "isHLtitle": "true",
        }
        headers = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.cninfo.com.cn"}
        session = make_session()
        try:
            resp = session.post(url, data=payload, headers=headers, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            return data.get("announcements", [])
        except Exception as exc:
            print(f"[juchao] plate {plate} error: {exc}")
            return []

    raw_items = _fetch_plate("szse") + _fetch_plate("sse")
    items = []
    for row in raw_items:
        title = row.get("announcementTitle") or ""
        link = row.get("announcementUrl") or ""
        if link and not link.startswith("http"):
            link = "http://www.cninfo.com.cn/" + link.lstrip("/")
        pub = row.get("announcementTime")
        items.append(
            {
                "source": "巨潮资讯",
                "title_zh": str(title).strip(),
                "link": str(link).strip(),
                "pubDate": normalize_dt(pub),
            }
        )
    return items


def fetch_xueqiu() -> List[Dict]:
    token = os.getenv("XQ_TOKEN")
    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
    }
    if token:
        headers["Cookie"] = f"xq_a_token={token}" if "xq_a_token" not in token else token
    else:
        print("[xueqiu] missing XQ_TOKEN, request may be rejected")

    url = "https://stock.xueqiu.com/v5/stock/news/list.json"
    params = {"symbol": "SH000001", "count": 30, "source": "web"}
    session = make_session()
    try:
        resp = session.get(url, headers=headers, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        print(f"[xueqiu] fetch error: {exc}")
        return []

    items_raw = data.get("items", []) if isinstance(data, dict) else []
    items = []
    for item in items_raw:
        title = item.get("title") or ""
        link = item.get("target") or item.get("link") or ""
        pub = item.get("time") or item.get("created_at")
        items.append(
            {
                "source": "雪球",
                "title_zh": title.strip(),
                "link": str(link).strip(),
                "pubDate": normalize_dt(pub),
            }
        )
    return items


def merge_and_save(output_path: str = "news.json") -> None:
    all_items = []
    for fn in (fetch_cailian, fetch_sina_rss, fetch_juchao, fetch_xueqiu):
        items = fn()
        print(f"{fn.__name__}: {len(items)} items")
        all_items.extend(items)

    dedup: Dict[str, Dict] = {}
    for item in all_items:
        key = item.get("link") or item.get("title_zh")
        if key and key not in dedup:
            dedup[key] = item

    merged = sorted(dedup.values(), key=lambda x: x.get("pubDate", ""), reverse=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)
    print(f"saved {len(merged)} items to {output_path}")


if __name__ == "__main__":
    merge_and_save(os.getenv("NEWS_JSON_PATH", "news.json"))
