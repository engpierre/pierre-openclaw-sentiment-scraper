---
name: video_transcript
description: Finfluencer and spoken video transcript harvester extracting account-free YouTube video metadata, captions, and retail euphoria trigger density.
version: 1.1.0
user-invocable: true
---

# Video Transcript Harvester Skill (Tier 3 Finfluencer Euphoria)

## Overview
Wraps `harvesters/transcript_miner.py` using `yt-dlp` and `youtube-transcript-api` to discover top retail videos, parse spoken subtitles/captions, and scan for high-hype finfluencer triggers (`10x`, `moon`, `urgent`, `millionaire`, `parabolic`, `next nvidia`).

## Exact CLI Invocation
Execute directly using 100% absolute Windows paths:

```powershell
C:\Anti-Gravity-Core\pierre_openclaw_sentiment_scraper\.venv\Scripts\python.exe C:\Anti-Gravity-Core\pierre_openclaw_sentiment_scraper\harvesters\transcript_miner.py --ticker <TICKER> --limit 5
```

### Arguments
- `--ticker`: Stock or crypto symbol (e.g., `ORCL`, `NVDA`, `SPY`). Required.
- `--limit`: Maximum number of videos to sample (default: `5`, range `1-15`).

## Telemetry Contract (stdout JSON)
The script returns strictly valid JSON to `stdout`:

```json
{
  "tier": "Tier 3 (Finfluencer & Video Euphoria)",
  "ticker": "ORCL",
  "timestamp_utc": "2026-10-27T06:30:00.000000+00:00",
  "video_count": 5,
  "aggregate_views": 182400,
  "total_euphoria_triggers": 8,
  "hype_trigger_density": 0.5333,
  "retail_euphoria_risk": "MODERATE",
  "videos": [
    {
      "video_id": "iV7z55jmfa4",
      "title": "Why Insiders Are Loading Up on Oracle Stock",
      "uploader": "MarketWatchers",
      "view_count": 48200,
      "upload_date": "20261022",
      "url": "https://www.youtube.com/watch?v=iV7z55jmfa4",
      "has_transcript": true,
      "transcript_excerpt": "...",
      "euphoria_matches": ["urgent", "buy now"],
      "euphoria_match_count": 2
    }
  ],
  "circuit_breaker": {
    "status": "OK",
    "error_code": null,
    "source": "youtube"
  }
}
```

## Risk Scoring Protocol
- `hype_trigger_density >= 0.70` -> `retail_euphoria_risk: "HIGH"`
- `hype_trigger_density >= 0.35` -> `retail_euphoria_risk: "MODERATE"`
- `hype_trigger_density < 0.35` -> `retail_euphoria_risk: "LOW"`
- If YouTube blocks search requests or rate limits occur, `circuit_breaker.status` transitions to `"DEGRADED"`.

## Stop Conditions & Output Format
1. **Strict Isolation Rule:** NEVER search for, reference, or execute `16_sentiment_harvester`, `run_single_dossier.py`, `orchestration`, or any legacy trading scripts outside `C:\Anti-Gravity-Core\pierre_openclaw_sentiment_scraper\`.
2. **Deterministic Output:** Run ONLY the command specified above.
3. **Natural Language Synthesis:** Present a clean, natural-language summary to the user highlighting:
   - Total Videos Sampled & Aggregate Viewership
   - Finfluencer Hype Trigger Density (Scale 0.0 to 1.0)
   - Retail Overcrowding / Euphoria Risk Level (`LOW`, `MODERATE`, `HIGH`, `EXTREME`)
   - Key Spoken Transcript Themes from Creators
   *(Do NOT output raw JSON unless the user explicitly requests raw JSON).*
