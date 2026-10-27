# 🦅 Pierre OpenClaw Sentiment Scraper
> **Decoupled Multi-Agent Social & Macro Sentiment Harvesting Engine**  
> *Orchestrated by OpenClaw | Powered locally by Ollama (`gemma4:26b` @ `temperature=0.0`)*

---

## 1. Project Overview & Architectural Isolation

**Pierre OpenClaw Sentiment Scraper** is a decoupled, 100% passive multi-agent social and macro sentiment harvesting engine designed to quantify crowd psychology, retail hype velocity, and prediction market consensus.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ARCHITECTURE ISOLATION CONTRACT                       │
├──────────────────────────────────────┬──────────────────────────────────────┤
│ FAST LOOP (Execution Swarm)          │ SLOW LOOP (OpenClaw Sentiment Engine)│
│ • Hermes XO Execution Engine        │ • 30-Minute Autonomous Heartbeat     │
│ • Moomoo OpenD Broker Gateway        │ • 100% Passive Read-Only Harvesting   │
│ • Monotonic ATR Exit Ratchets        │ • Zero Social Logins / Zero Posting  │
│ • Microsecond Level 2 Order Books    │ • Ollama gemma4:26b Local Reasoning  │
└──────────────────────────────────────┴──────────────────────────────────────┘
                                  │
                                  ▼
               shared_signals/crowd_sentiment.json
```

### Core Invariants:
1. **Decoupled Slow-Loop Cadence:** Operates on an autonomous 30-minute heartbeat (`HEARTBEAT.md`). It never blocks or slows down fast-loop trade executions.
2. **Zero-Account / 100% Passive Harvesting:** No Twitter/X, Reddit, TikTok, or YouTube user logins, sessions, or automated posting. All data is collected via public endpoints, public RSS/JSON APIs, and anonymous transcript streams.
3. **Deterministic Local Inference:** Powered entirely by local Ollama running `gemma4:26b` at `temperature=0.0` for deterministic, reproducible extraction and synthesis. Zero cloud LLM API costs or rate-limit lockouts.
4. **Unidirectional Telemetry Contract:** Communicates with downstream execution systems strictly via atomic JSON writes to `shared_signals/crowd_sentiment.json`.

---

## 2. The 3-Tier Harvesting Matrix (BettaFish Pattern)

The engine implements the **BettaFish Multi-Agent Pattern**, deploying three specialized, non-overlapping harvesting sub-agents:

```
                          ┌──────────────────────────┐
                          │   shared_signals/        │
                          │   watchlist.txt          │
                          └─────────────┬────────────┘
                                        │
           ┌────────────────────────────┼────────────────────────────┐
           ▼                            ▼                            ▼
┌──────────────────────┐     ┌──────────────────────┐     ┌──────────────────────┐
│     SUB-AGENT 1      │     │     SUB-AGENT 2      │     │     SUB-AGENT 3      │
│   forum_harvester    │     │   video_transcript   │     │      macro_odds      │
├──────────────────────┤     ├──────────────────────┤     ├──────────────────────┤
│ • Reddit .json feeds │     │ • YouTube subtitles  │     │ • Polymarket odds    │
│   (wsb, stocks, etc) │     │ • TikTok transcripts │     │ • Kalshi event books │
│ • StockTwits streams │     │ • Account-free pipe  │     │ • Finnhub news flow  │
│ • HackerNews API     │     │ • Hype velocity      │     │ • Macro reality      │
└──────────┬───────────┘     └──────────┬───────────┘     └──────────┬───────────┘
           │                            │                            │
           └────────────────────────────┼────────────────────────────┘
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │   AGENT FORUM SYNTHESIS  │
                          │   (gemma4:26b local LLM) │
                          └─────────────┬────────────┘
                                        │
                                        ▼
                          ┌──────────────────────────┐
                          │      shared_signals/     │
                          │   crowd_sentiment.json   │
                          └──────────────────────────┘
```

### Sub-Agent 1: `forum_harvester` (Social Velocity & Comment Dynamics)
- **Feeds:** Public `.json` endpoints of Reddit (`r/wallstreetbets`, `r/stocks`, `r/investing`, `r/options`), StockTwits cashtag stream APIs, and HackerNews search.
- **Focus:** Quantifies raw mention count, positive/negative lexical ratios, and velocity deviations relative to 30-day baseline moving averages.

### Sub-Agent 2: `video_transcript` (Retail Euphoria & Exit Liquidity Thermometer)
- **Feeds:** Account-free extraction of spoken subtitles and transcripts from YouTube video captions and trending TikTok finance clips.
- **Focus:** Analyzes finfluencer keyword density ("moon", "short squeeze", "generational wealth", "all-in", "crash incoming"). Serves as a contrarian indicator identifying when retail hype has reached peak exhaustion (exit liquidity risk).

### Sub-Agent 3: `macro_odds` (Prediction Markets & Institutional News)
- **Feeds:** Public order books from Polymarket, Kalshi event contracts (Fed rate cuts, CPI prints, geopolitical outcomes), and Finnhub institutional market news.
- **Focus:** Anchors speculative social chatter against cold, real-money prediction market probability curves and verified corporate releases.

---

## 3. The "Agent Forum" Synthesis Layer

Raw sentiment metrics are often contradictory: retail traders can be extremely euphoric on a stock while prediction markets price in severe macro headwinds. 

Before publishing telemetry, OpenClaw convenes the **Agent Forum**:
1. **Adversarial Cross-Examination:** Local `gemma4:26b` ingests the isolated outputs from `forum_harvester`, `video_transcript`, and `macro_odds`.
2. **Divergence Detection:** The model identifies divergences between retail euphoria and macro reality:
   - *Example:* Retail Euphoria Index $> 85\%$ while Polymarket rate-cut odds drop $< 20\%$ triggers an immediate `RETAIL_EUPHORIA_TOP` risk flag.
3. **Consensus Formulation:** Calculates the final `recommended_risk_modifier` ($0.50$ to $1.20$), giving trading engines an empirical scalar to dynamically expand or contract trade sizing.

---

## 4. Deterministic JSON Output Contract

All synthesized telemetry is emitted to `shared_signals/crowd_sentiment.json` formatted under this strict schema:

```json
{
  "timestamp": "2026-10-27T10:30:00Z",
  "generated_at_edt": "2026-10-27 06:30:00 EDT",
  "pipeline_version": "1.0.0",
  "assets": {
    "NVDA": {
      "ticker": "NVDA",
      "metrics": {
        "reddit_stocktwits_sentiment": 0.78,
        "chatter_velocity_zscore": 2.14,
        "video_transcript_hype_velocity": 0.84,
        "polymarket_macro_alignment": 0.42,
        "retail_euphoria_risk": 0.89
      },
      "forum_synthesis": {
        "consensus_regime": "RETAIL_EUPHORIA_EXTREME",
        "divergence_flag": "MACRO_SENTIMENT_DIVERGENCE",
        "key_drivers": [
          "TikTok finfluencer call option volume spikes",
          "Kalshi semiconductor tariff probability widening",
          "StockTwits bullish message ratio at 92%"
        ],
        "summary": "Extreme social buzz and video transcript hype are decoupling from cooling macroeconomic contract odds. High vulnerability to liquidity flushes."
      },
      "recommended_risk_modifier": 0.70
    }
  }
}
```

---

## 5. Repository Directory Tree

```
pierre_openclaw_sentiment_scraper/
├── .gitignore                          # Strict exclusions for venv, secrets, logs
├── README.md                           # Master Architecture & Data Contract Spec
├── PROGRESS.md                         # Operational phase & milestone tracker
├── .venv/                              # Isolated Python 3.11 virtual environment
├── openclaw_config/                    # OpenClaw agent orchestration configurations
│   ├── SOUL.md                         # (Phase 3) Agent persona & behavioral directives
│   ├── HEARTBEAT.md                    # (Phase 3) Autonomous 30-minute cron loop
│   └── skills/                         # BettaFish pattern skill definitions
│       ├── forum_harvester/            # Reddit / StockTwits / HN skill definition
│       │   └── .gitkeep
│       ├── video_transcript/           # YouTube / TikTok caption extraction skill
│       │   └── .gitkeep
│       └── macro_odds/                 # Polymarket / Kalshi / Finnhub skill
│           └── .gitkeep
├── harvesters/                         # (Phase 4) Standalone Python 3.11 scrapers
│   └── .gitkeep
├── synthesis/                          # (Phase 5) Gemma 4 26B agent forum engine
│   └── .gitkeep
└── shared_signals/                     # Cross-project telemetry output directory
    ├── .gitkeep
    ├── watchlist.txt                   # Target ticker registry (seeded)
    └── crowd_sentiment.json            # Deterministic telemetry contract output
```

---

## 6. Development & Execution Roadmap

- [x] **Phase 1:** Workspace, Python 3.11 Venv & GitHub Initialization
- [x] **Phase 2:** Governance & Architecture Specification (`README.md`, `PROGRESS.md`, `watchlist.txt`)
- [ ] **Phase 3:** OpenClaw Core Identity (`SOUL.md`) & Autonomous Polling (`HEARTBEAT.md`)
- [ ] **Phase 4:** Passive Harvester Skills (`SKILL.md` + Python 3.11 Harvesters)
- [ ] **Phase 5:** Agent Forum Synthesis Layer & End-to-End Dry Run
