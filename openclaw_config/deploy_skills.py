import os
import shutil
from pathlib import Path

source_skills = Path(r"C:\Anti-Gravity-Core\pierre_openclaw_sentiment_scraper\openclaw_config\skills")
skill_names = ["forum_harvester", "video_transcript", "macro_odds", "crowd_sentinel_forum"]

targets = [
    Path(r"C:\Users\Pierre\.openclaw\skills"),
    Path(r"C:\Users\Pierre\.openclaw\workspace\skills"),
    Path(r"C:\Users\Pierre\.openclaw\workspace\pierre-quant\skills"),
    Path(r"C:\Users\Pierre\.openclaw\workspace-supervisor\skills"),
    Path(r"C:\Anti-Gravity-Core\tools\skills"),
]

for target in targets:
    target.mkdir(parents=True, exist_ok=True)
    print(f"Deploying skills to: {target}")
    for sname in skill_names:
        src = source_skills / sname
        dst = target / sname
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        skill_file = dst / "SKILL.md"
        print(f"  -> Copied {sname}: SKILL.md exists={skill_file.exists()}, size={skill_file.stat().st_size} bytes")

print("All skills successfully deployed!")
