---
name: video-transcript
description: Finfluencer and spoken video transcript harvester extracting account-free YouTube video metadata, captions, and retail euphoria trigger density.
version: 1.0.0
---

# Video Transcript Harvester Skill (Tier 3 Finfluencer Euphoria)

## Overview
Wraps `harvesters/transcript_miner.py` using `yt-dlp` and `youtube-transcript-api` to discover top retail videos, parse spoken subtitles/captions, and scan for high-hype finfluencer triggers (`10x`, `moon`, `urgent`, `millionaire`, `parabolic`, `next nvidia`).

## CLI Invocation
Execute via the local isolated Python 3.11 virtual environment:

```powershell
.\.venv\Scripts\python.exe harvesters/transcript_miner.py --ticker <TICKER> --limit 5
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
