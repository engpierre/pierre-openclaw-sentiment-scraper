#!/usr/bin/env python3
"""
harvesters/transcript_miner.py - Tier 3 Finfluencer & Video Transcript Harvester
Extracts account-free YouTube video metadata and spoken transcripts using yt-dlp and youtube-transcript-api.
Scans for euphoria/hype keywords and quantifies retail FOMO / overcrowding.
Output: Strictly valid JSON to stdout.
"""

import argparse
import datetime
import json
import re
import sys
import time
from typing import Any, Dict, List

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi

EUPHORIA_TRIGGERS = [
    r"\b10x\b",
    r"\b100x\b",
    r"\bmoon\b",
    r"\burgent\b",
    r"\bbuy now\b",
    r"\bcrash\b",
    r"\bmillionaire\b",
    r"\bunstoppable\b",
    r"\bparabolic\b",
    r"\bexplode\b",
    r"\bexploding\b",
    r"\bmassive rally\b",
    r"\ball in\b",
    r"\blifetime opportunity\b",
    r"\bnext nvidia\b",
    r"\bgenerational wealth\b",
    r"\bshort squeeze\b",
]

COMPILED_EUPHORIA = [re.compile(pat, re.IGNORECASE) for pat in EUPHORIA_TRIGGERS]


import concurrent.futures

def extract_transcript_text(video_id: str, timeout_sec: float = 3.5) -> str:
    """Safely retrieve video transcript text with a strict timeout to prevent hangs."""
    def _fetch():
        try:
            yta = YouTubeTranscriptApi()
            if hasattr(yta, "fetch"):
                fetched = yta.fetch(video_id)
                if hasattr(fetched, "snippets"):
                    return " ".join(s.text for s in fetched.snippets)
                elif hasattr(fetched, "to_raw_data"):
                    return " ".join(s.get("text", "") for s in fetched.to_raw_data())
            if hasattr(YouTubeTranscriptApi, "get_transcript"):
                raw = YouTubeTranscriptApi.get_transcript(video_id)
                return " ".join(s.get("text", "") for s in raw)
        except Exception:
            pass
        return ""

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_fetch)
        try:
            return future.result(timeout=timeout_sec)
        except Exception:
            return ""


def scan_euphoria_triggers(text: str) -> Dict[str, Any]:
    matched_triggers = []
    total_matches = 0
    for pat in COMPILED_EUPHORIA:
        matches = pat.findall(text)
        if matches:
            matched_triggers.append(pat.pattern.replace(r"\b", "").lower())
            total_matches += len(matches)
    return {
        "matched_triggers": matched_triggers,
        "total_matches": total_matches,
    }


def harvest_youtube_videos(ticker: str, limit: int) -> Dict[str, Any]:
    circuit_breaker = {"status": "OK", "error_code": None, "source": "youtube"}
    sample_limit = min(limit, 5)
    search_query = f"ytsearch{sample_limit}:{ticker} stock analysis"

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "skip_download": True,
        "extract_flat": True,
        "socket_timeout": 5,
    }

    videos: List[Dict[str, Any]] = []

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            search_res = ydl.extract_info(search_query, download=False)
            entries = search_res.get("entries", []) if search_res else []

            for entry in entries[:sample_limit]:
                if not entry:
                    continue
                video_id = entry.get("id")
                title = entry.get("title", "")
                view_count = entry.get("view_count") or 0
                upload_date = entry.get("upload_date") or ""
                uploader = entry.get("uploader") or ""
                webpage_url = entry.get("url") or f"https://www.youtube.com/watch?v={video_id}"

                # Extract spoken transcript with fast timeout
                transcript_text = extract_transcript_text(video_id, timeout_sec=3.0) if video_id else ""
                transcript_snippet = transcript_text[:1200]

                # Euphoria scan across title + description + transcript
                corpus = f"{title} {entry.get('description', '')[:300]} {transcript_snippet}"
                fomo_scan = scan_euphoria_triggers(corpus)

                videos.append({
                    "video_id": video_id,
                    "title": title,
                    "uploader": uploader,
                    "view_count": view_count,
                    "upload_date": upload_date,
                    "url": webpage_url,
                    "has_transcript": bool(transcript_text),
                    "transcript_excerpt": transcript_snippet[:350],
                    "euphoria_matches": fomo_scan["matched_triggers"],
                    "euphoria_match_count": fomo_scan["total_matches"],
                })

    except Exception as exc:
        circuit_breaker["status"] = "DEGRADED"
        circuit_breaker["error_detail"] = str(exc)

    return {"videos": videos, "circuit_breaker": circuit_breaker}


def main():
    parser = argparse.ArgumentParser(description="Tier 3 Finfluencer & Video Transcript Harvester")
    parser.add_argument("--ticker", required=True, help="Stock or crypto ticker symbol (e.g. ORCL, NVDA)")
    parser.add_argument("--limit", type=int, default=3, help="Number of videos to sample (default: 3)")
    args = parser.parse_args()

    ticker = args.ticker.upper().strip()
    limit = max(1, min(args.limit, 15))

    harvest_res = harvest_youtube_videos(ticker, limit)
    videos = harvest_res["videos"]
    cb = harvest_res["circuit_breaker"]

    total_views = sum(v["view_count"] for v in videos)
    total_euphoria_matches = sum(v["euphoria_match_count"] for v in videos)

    # Euphoria trigger density score: normalized 0.0 to 1.0
    # 0 matches -> 0.0, >= 5 matches across videos -> 1.0
    density_score = min(1.0, round(total_euphoria_matches / max(1, len(videos) * 1.5), 4))

    # Overcrowding / Euphoria risk classification
    if density_score >= 0.70:
        euphoria_risk = "HIGH"
    elif density_score >= 0.35:
        euphoria_risk = "MODERATE"
    else:
        euphoria_risk = "LOW"

    output = {
        "tier": "Tier 3 (Finfluencer & Video Euphoria)",
        "ticker": ticker,
        "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "video_count": len(videos),
        "aggregate_views": total_views,
        "total_euphoria_triggers": total_euphoria_matches,
        "hype_trigger_density": density_score,
        "retail_euphoria_risk": euphoria_risk,
        "videos": videos,
        "circuit_breaker": cb,
    }

    print(json.dumps(output, indent=2))
    sys.exit(0)


if __name__ == "__main__":
    main()
