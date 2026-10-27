---
name: forum-harvester
description: Passive retail sentiment and cashtag momentum harvester querying Reddit (r/wallstreetbets, r/stocks, r/investing), HackerNews Algolia, and StockTwits streams with Yahoo RSS fallback.
version: 1.0.0
---

# Forum & Cashtag Harvester Skill (Tier 2 Retail Momentum)

## Overview
Wraps `harvesters/reddit_stocktwits.py` to collect passive retail chatter, cashtag velocity, and keyword sentiment polarity without requiring user logins or elevated API keys.

## CLI Invocation
Execute via the local isolated Python 3.11 virtual environment:

```powershell
.\.venv\Scripts\python.exe harvesters/reddit_stocktwits.py --ticker <TICKER> --limit 15
```

### Arguments
- `--ticker`: Stock or crypto symbol (e.g., `ORCL`, `NVDA`, `BTC-USD`). Required.
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
- The supervisor suppresses alerts unless `overall_status` trips to `"TRIPPED"`.
