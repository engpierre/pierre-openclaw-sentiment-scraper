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

    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/search.json"
        params = {
            "q": ticker,
            "restrict_sr": "1",
            "sort": "new",
            "limit": str(limit),
        }
        try:
            resp = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if resp.status_code in (429, 403):
                circuit_breaker["status"] = "DEGRADED"
                circuit_breaker["error_code"] = resp.status_code
                continue
            if resp.status_code == 200:
                data = resp.json()
                children = data.get("data", {}).get("children", [])
                for child in children:
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
        except Exception as exc:
            circuit_breaker["status"] = "DEGRADED"
            circuit_breaker["error_detail"] = str(exc)

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
