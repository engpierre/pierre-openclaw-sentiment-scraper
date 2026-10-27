#!/usr/bin/env python3
"""
harvesters/odds_news_baseline.py - Tier 1 Smart-Money Odds & Institutional News Harvester
Collects macro prediction market contracts from Polymarket and Kalshi, plus institutional news from Finnhub (with Yahoo RSS fallback).
Output: Strictly valid JSON to stdout.
"""

import argparse
import datetime
import json
import os
import re
import sys
from typing import Any, Dict, List

import feedparser
import requests
from dotenv import load_dotenv

load_dotenv()

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CrowdSentinel/1.0"
REQUEST_TIMEOUT = 10.0


def fetch_polymarket_odds(ticker: str, limit: int, session: requests.Session) -> Dict[str, Any]:
    url = "https://gamma-api.polymarket.com/events"
    params = {
        "limit": str(limit),
        "active": "true",
        "closed": "false",
    }
    markets_out = []
    cb = {"status": "OK", "error_code": None, "source": "polymarket"}

    try:
        resp = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        if resp.status_code in (429, 403):
            cb["status"] = "DEGRADED"
            cb["error_code"] = resp.status_code
            return {"markets": markets_out, "circuit_breaker": cb}
        if resp.status_code == 200:
            events = resp.json()
            for ev in events:
                ev_title = ev.get("title", "")
                ev_desc = ev.get("description", "")
                for mkt in ev.get("markets", []):
                    question = mkt.get("question", "")
                    prices_raw = mkt.get("outcomePrices")
                    prob_yes = None
                    try:
                        if isinstance(prices_raw, str):
                            parsed = json.loads(prices_raw)
                            prob_yes = float(parsed[0]) if parsed else None
                        elif isinstance(prices_raw, list) and prices_raw:
                            prob_yes = float(prices_raw[0])
                    except Exception:
                        pass

                    markets_out.append({
                        "platform": "polymarket",
                        "event_title": ev_title,
                        "question": question,
                        "probability_yes": prob_yes,
                        "volume": mkt.get("volume"),
                        "end_date": mkt.get("endDate"),
                    })
    except Exception as exc:
        cb["status"] = "DEGRADED"
        cb["error_detail"] = str(exc)

    return {"markets": markets_out[:limit], "circuit_breaker": cb}


def fetch_kalshi_odds(limit: int, session: requests.Session) -> Dict[str, Any]:
    url = "https://api.elections.kalshi.com/trade-api/v2/markets"
    params = {
        "limit": str(limit),
        "status": "open",
    }
    markets_out = []
    cb = {"status": "OK", "error_code": None, "source": "kalshi"}

    try:
        resp = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
        if resp.status_code in (429, 403):
            cb["status"] = "DEGRADED"
            cb["error_code"] = resp.status_code
            return {"markets": markets_out, "circuit_breaker": cb}
        if resp.status_code == 200:
            data = resp.json()
            raw_markets = data.get("markets", [])
            for mkt in raw_markets[:limit]:
                yes_bid = mkt.get("yes_bid")
                yes_ask = mkt.get("yes_ask")
                last_price = mkt.get("last_price")
                implied_prob = None
                if last_price is not None:
                    implied_prob = round(last_price / 100.0, 4)
                elif yes_bid is not None and yes_ask is not None:
                    implied_prob = round(((yes_bid + yes_ask) / 2.0) / 100.0, 4)

                markets_out.append({
                    "platform": "kalshi",
                    "ticker": mkt.get("ticker_name"),
                    "title": mkt.get("title", ""),
                    "subtitle": mkt.get("subtitle", ""),
                    "implied_probability": implied_prob,
                    "close_date": mkt.get("close_date"),
                })
    except Exception as exc:
        cb["status"] = "DEGRADED"
        cb["error_detail"] = str(exc)

    return {"markets": markets_out, "circuit_breaker": cb}


def fetch_institutional_news(ticker: str, limit: int, session: requests.Session) -> Dict[str, Any]:
    api_key = os.getenv("FINNHUB_API_KEY")
    articles = []
    cb = {"status": "OK", "error_code": None, "source": "news"}

    if api_key and api_key.strip():
        # Try Finnhub API
        today = datetime.date.today()
        from_date = (today - datetime.timedelta(days=7)).isoformat()
        to_date = today.isoformat()
        url = "https://finnhub.io/api/v1/company-news"
        params = {
            "symbol": ticker,
            "from": from_date,
            "to": to_date,
            "token": api_key.strip(),
        }
        try:
            resp = session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            if resp.status_code == 200:
                raw_articles = resp.json()
                for art in raw_articles[:limit]:
                    articles.append({
                        "source": art.get("source", "Finnhub"),
                        "headline": art.get("headline", ""),
                        "summary": art.get("summary", "")[:300],
                        "datetime": art.get("datetime"),
                        "url": art.get("url", ""),
                    })
                return {"articles": articles, "circuit_breaker": cb, "provider": "finnhub"}
            else:
                cb["error_code"] = resp.status_code
        except Exception as exc:
            cb["error_detail"] = str(exc)

    # Automatic fallback to Yahoo Finance RSS
    rss_url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    try:
        feed = feedparser.parse(rss_url)
        for entry in feed.entries[:limit]:
            articles.append({
                "source": "Yahoo Finance RSS",
                "headline": entry.get("title", ""),
                "summary": entry.get("summary", "")[:300],
                "datetime": entry.get("published", ""),
                "url": entry.get("link", ""),
            })
    except Exception as exc:
        cb["status"] = "DEGRADED"
        cb["error_detail"] = str(exc)

    return {"articles": articles, "circuit_breaker": cb, "provider": "yahoo_finance_rss"}


def main():
    parser = argparse.ArgumentParser(description="Tier 1 Smart-Money Odds & Institutional News Harvester")
    parser.add_argument("--ticker", required=True, help="Stock or crypto ticker symbol (e.g. ORCL, NVDA)")
    parser.add_argument("--limit", type=int, default=15, help="Max entries per source (default: 15)")
    args = parser.parse_args()

    ticker = args.ticker.upper().strip()
    limit = max(1, min(args.limit, 30))

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    poly_res = fetch_polymarket_odds(ticker, limit, session)
    kalshi_res = fetch_kalshi_odds(limit, session)
    news_res = fetch_institutional_news(ticker, limit, session)

    # Combine prediction market signals
    all_odds = []
    all_odds.extend(poly_res["markets"])
    all_odds.extend(kalshi_res["markets"])

    # Determine overall circuit breaker
    cb_statuses = [
        poly_res["circuit_breaker"]["status"],
        kalshi_res["circuit_breaker"]["status"],
        news_res["circuit_breaker"]["status"],
    ]
    if all(s == "OK" for s in cb_statuses):
        overall_circuit = "OK"
    elif any(s == "OK" for s in cb_statuses):
        overall_circuit = "DEGRADED"
    else:
        overall_circuit = "TRIPPED"

    output = {
        "tier": "Tier 1 (Smart Money & Institutional Baseline)",
        "ticker": ticker,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "news_provider": news_res.get("provider", "unknown"),
        "news_headline_count": len(news_res["articles"]),
        "news_headlines": news_res["articles"][:10],
        "macro_contracts_sampled": len(all_odds),
        "prediction_market_sample": all_odds[:10],
        "circuit_breaker": {
            "overall_status": overall_circuit,
            "sources": {
                "polymarket": poly_res["circuit_breaker"],
                "kalshi": kalshi_res["circuit_breaker"],
                "institutional_news": news_res["circuit_breaker"],
            },
        },
    }

    print(json.dumps(output, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
