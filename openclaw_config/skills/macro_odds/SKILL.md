---
name: macro_odds
description: Smart-money prediction market odds and institutional news harvester querying Polymarket, Kalshi, and Finnhub (with Yahoo RSS fallback).
version: 1.1.0
user-invocable: true
---

# Macro Odds & News Baseline Skill (Tier 1 Smart-Money Baseline)

## Overview
Wraps `harvesters/odds_news_baseline.py` to extract decentralized prediction market probabilities (Polymarket and Kalshi) alongside institutional headline news from Finnhub or Yahoo Finance RSS.

## Exact CLI Invocation
Execute directly using 100% absolute Windows paths:

```powershell
C:\Anti-Gravity-Core\pierre_openclaw_sentiment_scraper\.venv\Scripts\python.exe C:\Anti-Gravity-Core\pierre_openclaw_sentiment_scraper\harvesters\odds_news_baseline.py --ticker <TICKER> --limit 15
```

### Arguments
- `--ticker`: Stock or crypto symbol (e.g., `ORCL`, `NVDA`, `SPY`). Required.
- `--limit`: Maximum number of entries to sample (default: `15`).

## Telemetry Contract (stdout JSON)
The script returns strictly valid JSON to `stdout`:

```json
{
  "tier": "Tier 1 (Smart Money & Institutional Baseline)",
  "ticker": "ORCL",
  "timestamp_utc": "2026-10-27T06:30:00.000000+00:00",
  "news_provider": "yahoo_finance_rss",
  "news_headline_count": 15,
  "news_headlines": [
    {
      "source": "Yahoo Finance RSS",
      "headline": "Oracle Expands Sovereign Cloud Infrastructure",
      "summary": "...",
      "datetime": "Tue, 27 Oct 2026 05:15:00 GMT",
      "url": "https://..."
    }
  ],
  "macro_contracts_sampled": 10,
  "prediction_market_sample": [
    {
      "platform": "polymarket",
      "event_title": "Fed Interest Rate Cut in November 2026?",
      "question": "Will the Fed cut rates by 25 bps?",
      "probability_yes": 0.88,
      "volume": "14250000"
    }
  ],
  "circuit_breaker": {
    "overall_status": "OK",
    "sources": {
      "polymarket": { "status": "OK", "error_code": null, "source": "polymarket" },
      "kalshi": { "status": "OK", "error_code": null, "source": "kalshi" },
      "institutional_news": { "status": "OK", "error_code": null, "source": "news" }
    }
  }
}
```

## Circuit Breaker & Fallback Protocol
- `FINNHUB_API_KEY`: If not provided in environment, the harvester automatically executes with Yahoo Finance RSS, ensuring zero unhandled exceptions or crashes.
- If Polymarket or Kalshi APIs return HTTP 429/403 or schema shifts, individual source circuit breakers degrade gracefully while news parsing continues.

## Stop Conditions & Output Format
1. **Strict Isolation Rule:** NEVER search for, reference, or execute `16_sentiment_harvester`, `run_single_dossier.py`, `orchestration`, or any legacy trading scripts outside `C:\Anti-Gravity-Core\pierre_openclaw_sentiment_scraper\`.
2. **Deterministic Output:** Run ONLY the command specified above.
3. **Natural Language Synthesis:** Present a clean, natural-language summary to the user highlighting:
   - Primary Institutional News Themes & Major Headlines
   - Prediction Market Probability Context (Polymarket & Kalshi Contracts)
   - Macro Alignment Assessment (Bullish/Neutral/Bearish)
   - Circuit Breaker Health Status
   *(Do NOT output raw JSON unless the user explicitly requests raw JSON).*
