---
name: forum_harvester
description: Passive retail sentiment and cashtag momentum harvester querying Reddit (r/wallstreetbets, r/stocks, r/investing), HackerNews Algolia, and StockTwits streams with Yahoo RSS fallback.
version: 1.1.0
user-invocable: true
---

# Forum & Cashtag Harvester Skill (Tier 2 Retail Momentum)

## Overview
Wraps `harvesters/reddit_stocktwits.py` to collect passive retail chatter, cashtag velocity, and keyword sentiment polarity without requiring user logins or elevated API keys.

## Exact CLI Invocation
Execute directly using 100% absolute Windows paths:

```powershell
C:\Anti-Gravity-Core\pierre_openclaw_sentiment_scraper\.venv\Scripts\python.exe C:\Anti-Gravity-Core\pierre_openclaw_sentiment_scraper\harvesters\reddit_stocktwits.py --ticker <TICKER> --limit 15
```

### Arguments
- `--ticker`: Stock or crypto symbol (e.g., `ORCL`, `NVDA`, `SPY`). Required.
- `--limit`: Maximum number of entries to sample per source (default: `15`).

## Telemetry Contract (stdout JSON)
The script returns strictly valid JSON to `stdout`:

```json
{
  "tier": "Tier 2 (Retail Momentum)",
  "ticker": "ORCL",
  "timestamp_utc": "2026-10-27T06:30:00.000000+00:00",
  "sample_size": 32,
  "recent_24h_velocity_count": 28,
  "sentiment_polarity": 0.4211,
  "bullish_ratio": 0.7105,
  "raw_counts": {
    "bullish_keyword_matches": 27,
    "bearish_keyword_matches": 11
  },
  "top_snippets": [
    {
      "source": "reddit/r/stocks",
      "title": "Oracle cloud growth accelerates",
      "excerpt": "...",
      "score": 142
    }
  ],
  "circuit_breaker": {
    "overall_status": "OK",
    "sources": {
      "reddit": { "status": "OK", "error_code": null, "source": "reddit" },
      "hackernews": { "status": "OK", "error_code": null, "source": "hackernews" },
      "stocktwits": { "status": "OK", "error_code": null, "source": "stocktwits" }
    }
  }
}
```

## Circuit Breaker Handling
- If any external endpoint returns HTTP 429 or 403, the source is marked `"status": "DEGRADED"`.
- If StockTwits is degraded or Cloudflare-blocked, the harvester automatically activates Yahoo Finance Community RSS fallback.

## Stop Conditions & Output Format
1. **Strict Isolation Rule:** NEVER search for, reference, or execute `16_sentiment_harvester`, `run_single_dossier.py`, `orchestration`, or any legacy trading scripts outside `C:\Anti-Gravity-Core\pierre_openclaw_sentiment_scraper\`.
2. **Deterministic Output:** Run ONLY the command specified above.
3. **Natural Language Synthesis:** Present a clean, natural-language summary to the user highlighting:
   - Sample Size & 24h Chatter Velocity
   - Bullish Ratio & Sentiment Polarity (Positive vs Negative)
   - Top Retail Discussion Themes & Excerpts
   - Circuit Breaker Health Status
   *(Do NOT output raw JSON unless the user explicitly requests raw JSON).*
