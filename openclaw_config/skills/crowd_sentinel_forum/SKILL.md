---
name: crowd_sentinel_forum
description: Runs the full 3-tier passive sentiment harvest and Gemma 4 26B Agent Forum cross-examination for one or more stock tickers, updating crowd_sentiment.json and returning a natural-language summary.
version: 1.0.0
user-invocable: true
---

# CrowdSentinel Agent Forum Synthesis Skill (Master Swarm Arbiter)

## Overview
Executes the master synthesis orchestrator `synthesis/agent_forum.py`. Automatically runs the 3 passive harvesters (Tier 2 Reddit/StockTwits, Tier 3 YouTube Video Transcripts, and Tier 1 Polymarket/Kalshi/News), conducts the 3-persona dialectical debate using local Gemma 4 26B, commits the results atomically to `shared_signals/crowd_sentiment.json`, and synthesizes a high-conviction risk verdict.

## Exact CLI Invocation
Execute directly using 100% absolute Windows paths:

### For a Single Target Ticker:
```powershell
C:\Anti-Gravity-Core\pierre_openclaw_sentiment_scraper\.venv\Scripts\python.exe C:\Anti-Gravity-Core\pierre_openclaw_sentiment_scraper\synthesis\agent_forum.py --tickers <TICKER>
```

### For the Full Active Watchlist Universe:
```powershell
C:\Anti-Gravity-Core\pierre_openclaw_sentiment_scraper\.venv\Scripts\python.exe C:\Anti-Gravity-Core\pierre_openclaw_sentiment_scraper\synthesis\agent_forum.py
```

## Telemetry Contract & State Inspection
After the command completes, read the state file:
`C:\Anti-Gravity-Core\pierre_openclaw_sentiment_scraper\shared_signals\crowd_sentiment.json`

The file schema:
```json
{
  "timestamp": "2026-10-27T20:44:25Z",
  "generated_at_edt": "2026-10-27 16:44:25 EDT",
  "pipeline_version": "1.0.0",
  "orchestrator": "OpenClaw_CrowdSentinel",
  "model": "gemma4:26b",
  "temperature": 0.0,
  "assets": {
    "<TICKER>": {
      "ticker": "<TICKER>",
      "metrics": {
        "reddit_stocktwits_sentiment": 0.65,
        "chatter_velocity_zscore": 1.5,
        "video_transcript_hype_velocity": 0.12,
        "polymarket_macro_alignment": 0.85,
        "retail_euphoria_risk": "LOW"
      },
      "forum_synthesis": {
        "consensus_regime": "BULLISH_CONFLUENCE",
        "divergence_flag": "NONE",
        "key_drivers": ["..."],
        "summary": "..."
      },
      "recommended_risk_modifier": 1.05
    }
  }
}
```

## Stop Conditions & Output Format
1. **Strict Isolation Rule:** NEVER search for, reference, or execute `orchestration\run_single_dossier.py`, `16_sentiment_harvester`, or any legacy trading scripts outside `C:\Anti-Gravity-Core\pierre_openclaw_sentiment_scraper\`.
2. **Deterministic Output:** Run ONLY the command specified above.
3. **Natural Language Synthesis:** Present a clean, executive summary to the user breaking down:
   - **Voice A (Retail Forums):** Sentiment polarity and chatter velocity.
   - **Voice B (Finfluencer Euphoria):** Hype density and overcrowding risk level (`LOW`, `MODERATE`, `HIGH`, `EXTREME`).
   - **Voice C (Macro & Institutional):** Alignment score and primary drivers from prediction markets/news.
   - **Agent Forum Verdict:** Consensus Regime (e.g., `BULLISH_CONFLUENCE`, `RETAIL_EUPHORIA_EXTREME`, `CAPITULATION_ACCUMULATION`, `STEADY_ACCUMULATION`).
   - **Divergence Flag:** (e.g., `NONE`, `MACRO_SENTIMENT_DIVERGENCE`, `RETAIL_PANIC_DISLOCATION`).
   - **Recommended Risk Modifier:** Sizing multiplier (`0.50` to `1.20`) for downstream risk managers.
   *(Do NOT output raw JSON unless the user explicitly requests raw JSON).*
