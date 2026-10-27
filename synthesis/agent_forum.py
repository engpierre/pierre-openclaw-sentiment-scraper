#!/usr/bin/env python3
"""
synthesis/agent_forum.py - OpenClaw Agent Forum Synthesis Orchestrator
Executes the 3 passive harvesters for all watchlist assets, conducts a 3-persona dialectical
cross-examination using local Gemma 4 26B (Ollama), and writes validated risk telemetry
atomically to shared_signals/crowd_sentiment.json.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

BASE_DIR = Path(__file__).resolve().parent.parent
PYTHON_EXE = BASE_DIR / ".venv" / "Scripts" / "python.exe"
if not PYTHON_EXE.exists():
    PYTHON_EXE = Path(sys.executable)

WATCHLIST_PATH = BASE_DIR / "shared_signals" / "watchlist.txt"
OUTPUT_PATH = BASE_DIR / "shared_signals" / "crowd_sentiment.json"
RUBRIC_PATH = BASE_DIR / "synthesis" / "forum_debate_prompt.md"

OLLAMA_CHAT_URL = "http://127.0.0.1:11434/api/chat"
MODEL_NAME = "gemma4:26b"
MODEL_TEMPERATURE = 0.0
MODEL_SEED = 42


def load_watchlist(path: Path) -> List[str]:
    if not path.exists():
        return ["ORCL", "NVDA", "MSFT", "SPY"]
    tickers = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            t = line.strip().upper()
            if t and not t.startswith("#"):
                tickers.append(t)
    return tickers or ["ORCL", "NVDA", "MSFT", "SPY"]


def run_harvester(script_rel_path: str, ticker: str, limit: int, timeout: int = 25) -> Dict[str, Any]:
    script_path = BASE_DIR / script_rel_path
    cmd = [
        str(PYTHON_EXE),
        str(script_path),
        "--ticker", ticker,
        "--limit", str(limit)
    ]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=str(BASE_DIR)
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return json.loads(proc.stdout)
        else:
            sys.stderr.write(f"Harvester error ({script_rel_path}): {proc.stderr[:200]}\n")
    except Exception as exc:
        sys.stderr.write(f"Exception running {script_rel_path} on {ticker}: {exc}\n")

    return {
        "tier": f"Fallback ({script_rel_path})",
        "ticker": ticker,
        "circuit_breaker": {"overall_status": "DEGRADED", "error_detail": "Execution timeout or failure"}
    }


def compute_baseline_metrics(
    ticker: str,
    tier2: Dict[str, Any],
    tier3: Dict[str, Any],
    tier1: Dict[str, Any]
) -> Dict[str, Any]:
    # Tier 2 (Forums)
    sentiment_ratio = tier2.get("bullish_ratio", 0.50)
    sample_size = tier2.get("sample_size", 0)
    recent_velocity = tier2.get("recent_24h_velocity_count", 0)
    # Estimate z-score roughly: normalized against median baseline of 15
    zscore = round((recent_velocity - 15.0) / 10.0, 2) if sample_size > 0 else 0.0

    # Tier 3 (Video Euphoria)
    hype_density = tier3.get("hype_trigger_density", 0.0)
    euphoria_risk = tier3.get("retail_euphoria_risk", "LOW")

    # Tier 1 (Macro / News)
    # Examine headlines for sentiment cues
    headlines = tier1.get("news_headlines", [])
    bull_words = {"growth", "upside", "buy", "record", "expands", "rally", "soar", "gain", "advances", "beats"}
    bear_words = {"lost", "drop", "cut", "risk", "debt", "threaten", "lawsuit", "slump", "fall", "downgrade"}
    h_bull = 0
    h_bear = 0
    for h in headlines:
        txt = (h.get("headline", "") + " " + h.get("summary", "")).lower()
        h_bull += sum(1 for w in bull_words if w in txt)
        h_bear += sum(1 for w in bear_words if w in txt)

    total_h = h_bull + h_bear
    if total_h > 0:
        macro_alignment = round(max(0.20, min(0.90, h_bull / total_h)), 2)
    else:
        macro_alignment = 0.55

    return {
        "reddit_stocktwits_sentiment": float(sentiment_ratio),
        "chatter_velocity_zscore": float(zscore),
        "video_transcript_hype_velocity": float(hype_density),
        "polymarket_macro_alignment": float(macro_alignment),
        "retail_euphoria_risk": euphoria_risk
    }


def build_forum_prompt(
    ticker: str,
    metrics: Dict[str, Any],
    tier2_raw: Dict[str, Any],
    tier3_raw: Dict[str, Any],
    tier1_raw: Dict[str, Any]
) -> str:
    snippets_t2 = tier2_raw.get("top_snippets", [])[:4]
    videos_t3 = tier3_raw.get("videos", [])[:3]
    video_summary = [
        {"title": v.get("title"), "views": v.get("view_count"), "triggers": v.get("euphoria_matches")}
        for v in videos_t3
    ]
    headlines_t1 = tier1_raw.get("news_headlines", [])[:4]
    prediction_mkts = tier1_raw.get("prediction_market_sample", [])[:3]

    prompt = f"""You are the Agent Forum Arbiter in OpenClaw. Cross-examine the three orthogonal sentiment telemetry feeds for {ticker} using the dialectical rubric.

### INGESTED TELEMETRY FOR {ticker}:
1. Voice A (Retail Momentum - Tier 2 Forums):
   - Sentiment Polarity: {metrics['reddit_stocktwits_sentiment']:.2f} (0.50=neutral, >0.70=bullish)
   - Chatter Velocity Z-score: {metrics['chatter_velocity_zscore']:.2f}
   - Sample Snippets: {json.dumps(snippets_t2, indent=1)}

2. Voice B (Finfluencer Euphoria Auditor - Tier 3 Videos):
   - Hype Trigger Density: {metrics['video_transcript_hype_velocity']:.2f}
   - Overcrowding Risk: {metrics['retail_euphoria_risk']}
   - Video Excerpts: {json.dumps(video_summary, indent=1)}

3. Voice C (Macro & Institutional Arbiter - Tier 1 Odds & News):
   - Macro Alignment Score: {metrics['polymarket_macro_alignment']:.2f}
   - Top Headlines: {json.dumps([h.get('headline') for h in headlines_t1], indent=1)}
   - Prediction Market Context: {json.dumps([p.get('event_title') for p in prediction_mkts], indent=1)}

### RULES:
- If Voice A is highly euphoric (>0.75) and Voice B has HIGH/EXTREME hype while Voice C is neutral/bearish, flag RETAIL_EUPHORIA_EXTREME, divergence MACRO_SENTIMENT_DIVERGENCE, risk modifier 0.50.
- If Voice A is bullish (>0.65) and Voice C confirms (>0.65) with low hype (<0.60), flag BULLISH_CONFLUENCE, divergence NONE, risk modifier 1.00 to 1.15.
- If panic selling and doom rhetoric dominate while macro remains resilient, flag CAPITULATION_ACCUMULATION, divergence RETAIL_PANIC_DISLOCATION, risk modifier 1.10.
- Otherwise, flag STEADY_ACCUMULATION or CHOPPY_EQUILIBRIUM, risk modifier 1.00.

Output MUST be strictly valid JSON matching this schema:
{{
  "ticker": "{ticker}",
  "metrics": {{
    "reddit_stocktwits_sentiment": {metrics['reddit_stocktwits_sentiment']:.2f},
    "chatter_velocity_zscore": {metrics['chatter_velocity_zscore']:.2f},
    "video_transcript_hype_velocity": {metrics['video_transcript_hype_velocity']:.2f},
    "polymarket_macro_alignment": {metrics['polymarket_macro_alignment']:.2f},
    "retail_euphoria_risk": "{metrics['retail_euphoria_risk']}"
  }},
  "forum_synthesis": {{
    "consensus_regime": "<REGIME>",
    "divergence_flag": "<NONE | MACRO_SENTIMENT_DIVERGENCE | RETAIL_PANIC_DISLOCATION>",
    "key_drivers": [
      "<driver 1>",
      "<driver 2>",
      "<driver 3>"
    ],
    "summary": "<2 sentence summary of debate>"
  }},
  "recommended_risk_modifier": <float between 0.50 and 1.20>
}}
"""
    return prompt


def query_ollama_forum(ticker: str, prompt: str, timeout: int = 45) -> Optional[Dict[str, Any]]:
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": "You are the Agent Forum Arbiter. Return ONLY a valid JSON object matching the requested schema. Do not include introductory or concluding conversational prose."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "stream": False,
        "options": {
            "temperature": MODEL_TEMPERATURE,
            "seed": MODEL_SEED
        }
    }
    try:
        resp = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=timeout)
        if resp.status_code == 200:
            content = resp.json().get("message", {}).get("content", "").strip()
            # Extract JSON block if wrapped in markdown
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
            if match:
                raw_json = match.group(1)
            else:
                raw_json = content
            parsed = json.loads(raw_json)
            if "ticker" in parsed and "metrics" in parsed and "forum_synthesis" in parsed:
                return parsed
    except Exception as exc:
        sys.stderr.write(f"Ollama inference error for {ticker}: {exc}\n")
    return None


def deterministic_fallback_synthesis(ticker: str, metrics: Dict[str, Any]) -> Dict[str, Any]:
    sent = metrics["reddit_stocktwits_sentiment"]
    hype = metrics["video_transcript_hype_velocity"]
    macro = metrics["polymarket_macro_alignment"]
    e_risk = metrics["retail_euphoria_risk"]

    if sent > 0.75 and (hype > 0.75 or e_risk in ("HIGH", "EXTREME")) and macro < 0.55:
        regime = "RETAIL_EUPHORIA_EXTREME"
        div = "MACRO_SENTIMENT_DIVERGENCE"
        modifier = 0.50
        drivers = [
            f"Voice A indicates overheated social momentum at {sent:.2f}",
            f"Voice B flags finfluencer overcrowding saturation (risk: {e_risk})",
            f"Voice C fails to confirm trend with macro alignment at {macro:.2f}"
        ]
        summary = "Extreme retail social chatter and finfluencer hype have decoupled from institutional baseline. Risk cut by 50% to prevent buying exit liquidity."
    elif sent < 0.35 and hype < 0.25 and macro > 0.55:
        regime = "CAPITULATION_ACCUMULATION"
        div = "RETAIL_PANIC_DISLOCATION"
        modifier = 1.15
        drivers = [
            f"Voice A captures retail capitulation and panic sentiment at {sent:.2f}",
            "Voice B detects near-zero finfluencer interest and negative buzz",
            f"Voice C institutional contracts remain firm with alignment at {macro:.2f}"
        ]
        summary = "Retail panic selling has created an asymmetric dislocation while institutional baseline remains stable. Asymmetric risk expansion favored."
    elif sent >= 0.60 and macro >= 0.60 and hype < 0.65:
        regime = "BULLISH_CONFLUENCE"
        div = "NONE"
        modifier = 1.05
        drivers = [
            f"Voice A demonstrates positive retail accumulation at {sent:.2f}",
            f"Voice C institutional news confirms constructive momentum at {macro:.2f}",
            "Voice B euphoria triggers remain within healthy, non-overheated limits"
        ]
        summary = "Constructive multi-tier confluence between retail sentiment and institutional baseline with subdued speculative frenzy."
    else:
        regime = "STEADY_ACCUMULATION"
        div = "NONE"
        modifier = 1.00
        drivers = [
            f"Voice A forum sentiment stable at {sent:.2f}",
            f"Voice B video transcript hype well-contained at {hype:.2f}",
            f"Voice C macro alignment in balance at {macro:.2f}"
        ]
        summary = "Balanced market conditions with moderate engagement across social and institutional tiers. Full baseline risk allocation permitted."

    return {
        "ticker": ticker,
        "metrics": metrics,
        "forum_synthesis": {
            "consensus_regime": regime,
            "divergence_flag": div,
            "key_drivers": drivers,
            "summary": summary
        },
        "recommended_risk_modifier": modifier
    }


def atomic_write_json(data: Dict[str, Any], target_path: Path):
    target_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = target_path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(temp_path, target_path)


def main():
    parser = argparse.ArgumentParser(description="OpenClaw Agent Forum Synthesis Orchestrator")
    parser.add_argument("--watchlist", type=str, default=str(WATCHLIST_PATH), help="Path to watchlist.txt")
    parser.add_argument("--output", type=str, default=str(OUTPUT_PATH), help="Path to crowd_sentiment.json")
    parser.add_argument("--tickers", type=str, default="", help="Comma-separated ticker list override")
    args = parser.parse_args()

    if args.tickers.strip():
        tickers = [t.strip().upper() for t in args.tickers.split(",") if t.strip()]
    else:
        tickers = load_watchlist(Path(args.watchlist))

    print(f"[CROWD_SENTINEL] Commencing Phase 5 Forum Synthesis for {len(tickers)} assets: {tickers}")
    t_start = time.time()

    assets_result: Dict[str, Any] = {}

    for ticker in tickers:
        print(f"\n--- Processing Asset: {ticker} ---")
        t0 = time.time()

        # Step 1: Run harvesters
        print(f"[{ticker}] 1/3 Harvesting Tier 2 (Reddit/StockTwits/HN)...")
        tier2_data = run_harvester("harvesters/reddit_stocktwits.py", ticker, limit=15)

        print(f"[{ticker}] 2/3 Harvesting Tier 3 (YouTube/Finfluencer transcripts)...")
        tier3_data = run_harvester("harvesters/transcript_miner.py", ticker, limit=5)

        print(f"[{ticker}] 3/3 Harvesting Tier 1 (Polymarket/Kalshi/News)...")
        tier1_data = run_harvester("harvesters/odds_news_baseline.py", ticker, limit=15)

        # Step 2: Compute normalized metrics
        metrics = compute_baseline_metrics(ticker, tier2_data, tier3_data, tier1_data)
        print(f"[{ticker}] Metrics: Sent={metrics['reddit_stocktwits_sentiment']:.2f}, Hype={metrics['video_transcript_hype_velocity']:.2f}, Macro={metrics['polymarket_macro_alignment']:.2f}, EuphoriaRisk={metrics['retail_euphoria_risk']}")

        # Step 3: Run Gemma 4 26B Dialectical Synthesis
        prompt = build_forum_prompt(ticker, metrics, tier2_data, tier3_data, tier1_data)
        print(f"[{ticker}] Invoking local Ollama {MODEL_NAME} for 3-persona forum debate...")
        synthesis_result = query_ollama_forum(ticker, prompt, timeout=50)

        if not synthesis_result:
            print(f"[{ticker}] Ollama busy or unparseable. Applying deterministic synthesis rubric...")
            synthesis_result = deterministic_fallback_synthesis(ticker, metrics)
        else:
            print(f"[{ticker}] LLM synthesis completed. Regime={synthesis_result.get('forum_synthesis', {}).get('consensus_regime')}")

        assets_result[ticker] = synthesis_result
        print(f"[{ticker}] Done in {round(time.time() - t0, 1)}s. Risk Modifier: {synthesis_result.get('recommended_risk_modifier')}")

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    # EDT offset = -4 hours
    now_edt = now_utc.astimezone(datetime.timezone(datetime.timedelta(hours=-4)))

    output_payload = {
        "timestamp": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_at_edt": now_edt.strftime("%Y-%m-%d %H:%M:%S EDT"),
        "pipeline_version": "1.0.0",
        "orchestrator": "OpenClaw_CrowdSentinel",
        "model": MODEL_NAME,
        "temperature": MODEL_TEMPERATURE,
        "assets": assets_result
    }

    out_file = Path(args.output)
    atomic_write_json(output_payload, out_file)
    print(f"\n[CROWD_SENTINEL] Atomic commit completed -> {out_file}")
    print(f"[CROWD_SENTINEL] Total pipeline execution time: {round(time.time() - t_start, 1)}s across {len(tickers)} assets.")


if __name__ == "__main__":
    main()
