# HEARTBEAT.md — Autonomous 30-Minute Polling Cycle

SCHEDULE: */30 * * * *
TIMEZONE: America/Toronto
AGENT: CrowdSentinel
SESSION_ISOLATION: ENABLED

---

## Autonomous Turn Execution Checklist

- [ ] **Step 1 (Watchlist & Inference Health Check):**
  - Read target ticker symbols line-by-line from `shared_signals/watchlist.txt`.
  - Perform GET probe to `http://localhost:11434/api/tags` to verify Ollama host is warm and `gemma4:26b` is resident.
  - If Ollama is unreachable, abort turn, log `CRITICAL_INFERENCE_OFFLINE`, and do NOT overwrite previous telemetry.

- [ ] **Step 2 (Parallel Skill Harvesting):**
  - For each active ticker, execute the 3 decoupled harvesting skills via local `.venv\Scripts\python.exe`:
    1. `openclaw_config/skills/forum_harvester/` (Reddit public JSON, StockTwits streams, HackerNews).
    2. `openclaw_config/skills/video_transcript/` (Account-free YouTube captions & TikTok finance clips).
    3. `openclaw_config/skills/macro_odds/` (Polymarket probability curves, Kalshi event contracts, Finnhub).
  - Collect structured JSON payloads per ticker into memory.

- [ ] **Step 3 (Circuit Breaker & Rate-Limit Audit):**
  - Verify process exit codes and HTTP response headers across all harvester passes.
  - **Circuit Breaker Protocol:** If any endpoint returns HTTP 429 (Rate Limit) or 403 (Forbidden) for 3 consecutive polls:
    - Trip the breaker for that specific source: pause its execution for 2 consecutive heartbeat cycles (60 minutes).
    - Log `CIRCUIT_BREAKER_TRIPPED: <SOURCE_NAME>` in operational telemetry.
    - Gracefully degrade: continue synthesis using the remaining operational tiers without halting the turn.

- [ ] **Step 4 (Agent Forum Cross-Examination):**
  - For each target ticker, submit the aggregated 3-tier telemetry to local `gemma4:26b` using `synthesis/forum_debate_prompt.md`.
  - Conduct the dialectic debate between Voice A (Retail Momentum), Voice B (Euphoria Auditor), and Voice C (Macro Arbiter).
  - Generate the consensus regime, divergence flags, key drivers, and `recommended_risk_modifier`.

- [ ] **Step 5 (Atomic JSON Commit & Status Suppression):**
  - Serialize the synthesized output adhering strictly to the `shared_signals/crowd_sentiment.json` schema.
  - Commit write atomically using temporary file swap (`crowd_sentiment.json.tmp` -> `crowd_sentiment.json`).
  - Output suppression: If all 5 checklist steps complete without active circuit breaker alerts or extreme euphoria spikes, terminate the session turn cleanly with:
    ```json
    {"status": "HEARTBEAT_OK", "timestamp_utc": "ISO8601", "tickers_evaluated": 4}
    ```
