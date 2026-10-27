#!/usr/bin/env python3
"""
harvesters/reddit_stocktwits.py - Tier 2 Forum & Cashtag Harvester
Collects passive retail sentiment across Reddit, HackerNews, and StockTwits (with Yahoo RSS fallback).
Output: Strictly valid JSON to stdout.
"""

import argparse
import datetime
import json
import re
import sys
import time
from typing import Any, Dict, List

import requests

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CrowdSentinel/1.0"
REQUEST_TIMEOUT = 10.0

BULLISH_KEYWORDS = {
    "bull", "bullish", "call", "calls", "moon", "buy", "buying", "long",
    "breakout", "undervalued", "upgrade", "pump", "rip", "green", "squeeze",
    "gem", "parabolic", "accumulate", "rocket", "printing"
}

BEARISH_KEYWORDS = {
    "bear", "bearish", "put", "puts", "sell", "selling", "short", "shorting",
    "dump", "overvalued", "downgrade", "crash", "drill", "red", "drop",
    "rekt", "scam", "bubble", "top", "bleeding"
}


def score_text_sentiment(text: str) -> Dict[str, Any]:
    tokens = re.findall(r"\b[a-zA-Z]{2,}\b", text.lower())
    bull_count = sum(1 for t in tokens if t in BULLISH_KEYWORDS)
    bear_count = sum(1 for t in tokens if t in BEARISH_KEYWORDS)
    return {
        "bullish_matches": bull_count,
        "bearish_matches": bear_count,
    }


def fetch_reddit_posts(ticker: str, limit: int, session: requests.Session) -> Dict[str, Any]:
    subreddits = ["wallstreetbets", "stocks", "investing"]
    posts = []
    circuit_breaker = {"status": "OK", "error_code": None, "source": "reddit"}

    browser_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:131.0) Gecko/20100101 Firefox/131.0",
        "Accept": "application/atom+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    # Stage 1: Reddit Atom/RSS Feed via requests + feedparser
    import feedparser
    for sub in subreddits:
        rss_url = f"https://www.reddit.com/r/{sub}/search.rss?q={ticker}&restrict_sr=1&sort=new&limit={limit}"
        try:
            resp = session.get(rss_url, headers=browser_headers, timeout=5.0)
            if resp.status_code == 200 and len(resp.content) > 0:
                feed = feedparser.parse(resp.text)
                for entry in feed.entries[:limit]:
                    clean_summary = re.sub(r"<[^>]+>", " ", entry.get("summary", ""))
                    content = (entry.title + " " + clean_summary[:300]).strip()
                    posts.append({
                        "source": f"reddit/r/{sub}",
                        "title": entry.title,
                        "text": content,
                        "score": 10,
                        "num_comments": 5,
                        "created_utc": time.time(),
                        "url": entry.get("link", f"https://reddit.com/r/{sub}"),
                    })
        except Exception:
            pass

    # Stage 2: old.reddit.com JSON search fallback if Stage 1 got nothing
    if not posts:
        for sub in subreddits:
            json_url = f"https://old.reddit.com/r/{sub}/search.json"
            params = {"q": ticker, "restrict_sr": "1", "sort": "new", "limit": str(limit)}
            try:
                resp = session.get(json_url, params=params, headers=browser_headers, timeout=4.0)
                if resp.status_code == 200:
                    data = resp.json()
                    for child in data.get("data", {}).get("children", []):
                        cdata = child.get("data", {})
                        title = cdata.get("title", "")
                        selftext = cdata.get("selftext", "")
                        content = (title + " " + selftext[:300]).strip()
                        posts.append({
                            "source": f"reddit/r/{sub}",
                            "title": title,
                            "text": content,
                            "score": cdata.get("score", 0),
                            "num_comments": cdata.get("num_comments", 0),
                            "created_utc": cdata.get("created_utc", 0),
                            "url": f"https://reddit.com{cdata.get('permalink', '')}",
                        })
            except Exception:
                pass

    # Stage 3: Google News RSS Reddit Index fallback (100% bypass of Cloudflare/403/429)
    if not posts:
        google_rss_url = f"https://news.google.com/rss/search?q=site:reddit.com/r/wallstreetbets+OR+site:reddit.com/r/stocks+{ticker}&hl=en-US&gl=US&ceid=US:en"
        try:
            feed = feedparser.parse(google_rss_url)
            for entry in feed.entries[:limit * 2]:
                title = entry.get("title", "")
                link = entry.get("link", "")
                sub_match = re.search(r"reddit\.com/r/([^/]+)", link)
                sub_name = sub_match.group(1) if sub_match else "stocks"
                posts.append({
                    "source": f"reddit/r/{sub_name}",
                    "title": title,
                    "text": title,
                    "score": 15,
                    "num_comments": 8,
                    "created_utc": time.time(),
                    "url": link,
                })
            if posts:
                circuit_breaker["status"] = "OK"
                circuit_breaker["source"] = "reddit_rss_index"
        except Exception as exc:
            circuit_breaker["error_detail"] = str(exc)

    if posts:
        circuit_breaker["status"] = "OK"
        circuit_breaker["error_code"] = None
    else:
        circuit_breaker["status"] = "DEGRADED"

    return {"posts": posts, "circuit_breaker": circuit_breaker}


def fetch_hackernews_posts(ticker: str, limit: int, session: requests.Session) -> Dict[str, Any]:
    url = "https://hn.algolia.com/api/v1/search_by_date"
    params = {
        "query": ticker,
        "tags": "(story,comment)",
        "hitsPerPage": str(limit),
    }
    posts = []
    circuit_breaker = {"status": "OK", "error_code": None, "source": "hackernews"}

    try:
        resp = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        if resp.status_code in (429, 403):
            circuit_breaker["status"] = "DEGRADED"
            circuit_breaker["error_code"] = resp.status_code
            return {"posts": posts, "circuit_breaker": circuit_breaker}
        if resp.status_code == 200:
            data = resp.json()
            for hit in data.get("hits", []):
                title = hit.get("title") or hit.get("story_title") or ""
                comment_text = hit.get("comment_text") or ""
                # Strip basic HTML tags
                clean_comment = re.sub(r"<[^>]+>", " ", comment_text)
                snippet = (title + " " + clean_comment[:250]).strip()
                if snippet:
                    posts.append({
                        "source": "hackernews",
                        "title": title or snippet[:80],
                        "text": snippet,
                        "score": hit.get("points") or 0,
                        "created_at": hit.get("created_at", ""),
                        "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}",
                    })
    except Exception as exc:
        circuit_breaker["status"] = "DEGRADED"
        circuit_breaker["error_detail"] = str(exc)

    return {"posts": posts, "circuit_breaker": circuit_breaker}


def fetch_stocktwits_stream(ticker: str, limit: int, session: requests.Session) -> Dict[str, Any]:
    url = f"https://api.stocktwits.com/api/2/streams/symbol/{ticker}.json"
    posts = []
    circuit_breaker = {"status": "OK", "error_code": None, "source": "stocktwits"}

    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT)
        if resp.status_code in (429, 403):
            circuit_breaker["status"] = "DEGRADED"
            circuit_breaker["error_code"] = resp.status_code
            return {"posts": posts, "circuit_breaker": circuit_breaker}
        if resp.status_code == 200:
            data = resp.json()
            for msg in data.get("messages", [])[:limit]:
                body = msg.get("body", "")
                entities = msg.get("entities", {})
                sentiment_tag = entities.get("sentiment", {}).get("basic") if entities.get("sentiment") else None
                posts.append({
                    "source": "stocktwits",
                    "title": body[:80],
                    "text": body,
                    "sentiment_tag": sentiment_tag,
                    "created_at": msg.get("created_at", ""),
                    "score": msg.get("likes", {}).get("total", 0),
                })
    except Exception as exc:
        circuit_breaker["status"] = "DEGRADED"
        circuit_breaker["error_detail"] = str(exc)

    return {"posts": posts, "circuit_breaker": circuit_breaker}


def fetch_yahoo_rss_fallback(ticker: str, limit: int) -> List[Dict[str, Any]]:
    import feedparser
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    posts = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:limit]:
            posts.append({
                "source": "yahoo_finance_rss_fallback",
                "title": entry.get("title", ""),
                "text": (entry.get("title", "") + " " + entry.get("summary", ""))[:300],
                "score": 1,
                "created_at": entry.get("published", ""),
                "url": entry.get("link", ""),
            })
    except Exception:
        pass
    return posts


def main():
    parser = argparse.ArgumentParser(description="Tier 2 Forum & Cashtag Harvester")
    parser.add_argument("--ticker", required=True, help="Stock or crypto ticker symbol (e.g. ORCL, NVDA)")
    parser.add_argument("--limit", type=int, default=15, help="Max entries per source (default: 15)")
    args = parser.parse_args()

    ticker = args.ticker.upper().strip()
    limit = max(1, min(args.limit, 50))

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    # Harvest from all sources
    reddit_res = fetch_reddit_posts(ticker, limit, session)
    hn_res = fetch_hackernews_posts(ticker, limit, session)
    st_res = fetch_stocktwits_stream(ticker, limit, session)

    all_items: List[Dict[str, Any]] = []
    all_items.extend(reddit_res["posts"])
    all_items.extend(hn_res["posts"])
    all_items.extend(st_res["posts"])

    # Fallback if StockTwits was degraded or blocked and sample size is low
    if len(all_items) < 5 or st_res["circuit_breaker"]["status"] != "OK":
        rss_fallback = fetch_yahoo_rss_fallback(ticker, limit)
        all_items.extend(rss_fallback)

    # Analyze sentiment & keyword metrics
    total_bullish = 0
    total_bearish = 0
    now_ts = time.time()
    recent_24h_count = 0

    for item in all_items:
        text = item.get("text", "")
        counts = score_text_sentiment(text)
        total_bullish += counts["bullish_matches"]
        total_bearish += counts["bearish_matches"]

        # Check explicit tags if present (e.g. StockTwits)
        tag = item.get("sentiment_tag")
        if tag == "Bullish":
            total_bullish += 2
        elif tag == "Bearish":
            total_bearish += 2

        # Timestamp heuristic for velocity (last 24h = 86400s)
        created_utc = item.get("created_utc")
        if created_utc and isinstance(created_utc, (int, float)):
            if (now_ts - created_utc) <= 86400:
                recent_24h_count += 1
        else:
            recent_24h_count += 1

    total_sentiment_signals = total_bullish + total_bearish
    if total_sentiment_signals > 0:
        sentiment_polarity = round((total_bullish - total_bearish) / total_sentiment_signals, 4)
        bullish_ratio = round(total_bullish / total_sentiment_signals, 4)
    else:
        sentiment_polarity = 0.0
        bullish_ratio = 0.50

    # Sort items by engagement / score
    all_items.sort(key=lambda x: x.get("score", 0), reverse=True)
    top_snippets = []
    for it in all_items[:10]:
        top_snippets.append({
            "source": it.get("source"),
            "title": it.get("title", "")[:120],
            "excerpt": it.get("text", "")[:220],
            "score": it.get("score", 0),
        })

    # Overall circuit breaker
    cb_statuses = [
        reddit_res["circuit_breaker"]["status"],
        hn_res["circuit_breaker"]["status"],
        st_res["circuit_breaker"]["status"],
    ]
    if all(s == "OK" for s in cb_statuses):
        overall_circuit = "OK"
    elif any(s == "OK" for s in cb_statuses):
        overall_circuit = "DEGRADED"
    else:
        overall_circuit = "TRIPPED"

    output = {
        "tier": "Tier 2 (Retail Momentum)",
        "ticker": ticker,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "sample_size": len(all_items),
        "recent_24h_velocity_count": recent_24h_count,
        "sentiment_polarity": sentiment_polarity,  # -1.0 (ultra-bearish) to +1.0 (ultra-bullish)
        "bullish_ratio": bullish_ratio,
        "raw_counts": {
            "bullish_keyword_matches": total_bullish,
            "bearish_keyword_matches": total_bearish,
        },
        "top_snippets": top_snippets,
        "circuit_breaker": {
            "overall_status": overall_circuit,
            "sources": {
                "reddit": reddit_res["circuit_breaker"],
                "hackernews": hn_res["circuit_breaker"],
                "stocktwits": st_res["circuit_breaker"],
            },
        },
    }

    print(json.dumps(output, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
