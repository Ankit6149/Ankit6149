"""Fetch public LeetCode statistics and render theme-aware profile cards."""

from __future__ import annotations

import argparse
import json
import urllib.request
from dataclasses import dataclass
from html import escape
from pathlib import Path

GRAPHQL_URL = "https://leetcode.com/graphql"
QUERY = """
query profileCard($username: String!) {
  matchedUser(username: $username) {
    username
    submitStatsGlobal {
      acSubmissionNum {
        difficulty
        count
        submissions
      }
    }
    profile {
      ranking
    }
    languageProblemCount {
      languageName
      problemsSolved
    }
  }
}
"""


@dataclass
class Profile:
    username: str
    total: int
    easy: int
    medium: int
    hard: int
    ranking: int | None
    languages: list[tuple[str, int]]


def fetch_profile(username: str) -> Profile:
    payload = json.dumps(
        {"query": QUERY, "variables": {"username": username}}
    ).encode("utf-8")
    request = urllib.request.Request(
        GRAPHQL_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 GitHub-Profile-Card",
            "Referer": f"https://leetcode.com/u/{username}/",
        },
    )
    with urllib.request.urlopen(request, timeout=25) as response:
        result = json.loads(response.read().decode("utf-8"))

    if result.get("errors"):
        raise RuntimeError(result["errors"][0].get("message", "LeetCode query failed"))

    user = result.get("data", {}).get("matchedUser")
    if not user:
        raise RuntimeError(f"LeetCode user {username!r} was not found")

    counts = {
        item["difficulty"]: int(item["count"])
        for item in user["submitStatsGlobal"]["acSubmissionNum"]
    }
    languages = sorted(
        [
            (item["languageName"], int(item["problemsSolved"]))
            for item in user.get("languageProblemCount", [])
            if int(item.get("problemsSolved", 0)) > 0
        ],
        key=lambda item: (-item[1], item[0].lower()),
    )

    return Profile(
        username=user["username"],
        total=counts.get("All", 0),
        easy=counts.get("Easy", 0),
        medium=counts.get("Medium", 0),
        hard=counts.get("Hard", 0),
        ranking=user.get("profile", {}).get("ranking"),
        languages=languages,
    )


def language_chips(languages: list[tuple[str, int]], theme: str) -> str:
    if theme == "light":
        fill, stroke, text = "#f6f8fa", "#d0d7de", "#24292f"
    else:
        fill, stroke, text = "#161b22", "#30363d", "#f0f6fc"

    x, y = 632.0, 304.0
    max_x = 1118.0
    line_height = 36.0
    output: list[str] = []

    for language, solved in languages:
        label = f"{language} {solved}"
        width = max(70.0, 26.0 + len(label) * 7.5)
        if x + width > max_x:
            x = 632.0
            y += line_height
        output.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="28" '
            f'rx="14" fill="{fill}" stroke="{stroke}"/>'
            f'<text x="{x + width / 2:.1f}" y="{y + 19:.1f}" text-anchor="middle" '
            f'class="mono" fill="{text}">{escape(label)}</text>'
        )
        x += width + 10.0

    return "".join(output)


def render(profile: Profile, theme: str) -> str:
    dark = theme == "dark"
    background = "#0d1117" if dark else "#ffffff"
    panel = "#161b22" if dark else "#f6f8fa"
    border = "#30363d" if dark else "#d0d7de"
    text = "#f0f6fc" if dark else "#24292f"
    muted = "#8b949e" if dark else "#57606a"
    track = "#30363d" if dark else "#d8dee4"
    accent = "#2f9e8f"
    easy = "#2f9e8f"
    medium = "#bf8700" if dark else "#9a6700"
    hard = "#6e8ec6" if dark else "#576f9e"

    max_count = max(profile.easy, profile.medium, profile.hard, 1)
    easy_width = 246 * profile.easy / max_count
    medium_width = 246 * profile.medium / max_count
    hard_width = 246 * profile.hard / max_count
    ranking = f"{profile.ranking:,}" if profile.ranking else "Not ranked"
    primary = profile.languages[0][0] if profile.languages else "None"
    solved_arc = min(1.0, profile.total / 1000.0)
    dash = 408.4 * solved_arc

    chips = language_chips(profile.languages, theme)
    height = 398 if len(profile.languages) <= 5 else 432

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1160" height="{height}" viewBox="0 0 1160 {height}" role="img" aria-labelledby="title desc">
<title id="title">LeetCode profile for {escape(profile.username)}</title>
<desc id="desc">{profile.total} solved problems, ranking {escape(ranking)}, with difficulty and language breakdown.</desc>
<style>
  .title {{ font: 600 24px -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; }}
  .name {{ font: 600 26px -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; }}
  .metric {{ font: 600 32px -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; }}
  .body {{ font: 400 15px -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; }}
  .label {{ font: 600 12px -apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif; letter-spacing: .7px; }}
  .mono {{ font: 500 12px ui-monospace,SFMono-Regular,SF Mono,Menlo,Consolas,monospace; }}
</style>
<rect x="1" y="1" width="1158" height="{height - 2}" rx="12" fill="{background}" stroke="{border}"/>
<rect x="24" y="24" width="520" height="{height - 48}" rx="10" fill="{panel}" stroke="{border}"/>
<text x="52" y="58" class="label" fill="{accent}">LEETCODE</text>
<text x="52" y="94" class="name" fill="{text}">{escape(profile.username)}</text>
<text x="52" y="122" class="body" fill="{muted}">Problem solving profile</text>

<circle cx="156" cy="235" r="65" fill="none" stroke="{track}" stroke-width="9"/>
<circle cx="156" cy="235" r="65" fill="none" stroke="{accent}" stroke-width="9" stroke-linecap="round" stroke-dasharray="{dash:.1f} 408.4" transform="rotate(-90 156 235)"/>
<text x="156" y="229" text-anchor="middle" class="metric" fill="{text}">{profile.total}</text>
<text x="156" y="257" text-anchor="middle" class="label" fill="{muted}">TOTAL SOLVED</text>

<text x="286" y="196" class="label" fill="{muted}">RANKING</text>
<text x="286" y="232" class="metric" fill="{text}">{escape(ranking)}</text>
<text x="286" y="282" class="label" fill="{muted}">PRIMARY LANGUAGE</text>
<text x="286" y="318" class="metric" fill="{text}">{escape(primary)}</text>

<text x="604" y="58" class="title" fill="{text}">Solved breakdown</text>
<text x="604" y="86" class="body" fill="{muted}">Difficulty, ranking, and every language used</text>

<text x="604" y="130" class="label" fill="{muted}">EASY</text>
<rect x="604" y="144" width="246" height="10" rx="5" fill="{track}"/>
<rect x="604" y="144" width="{easy_width:.1f}" height="10" rx="5" fill="{easy}"/>
<text x="876" y="154" class="body" fill="{text}">{profile.easy}</text>

<text x="604" y="183" class="label" fill="{muted}">MEDIUM</text>
<rect x="604" y="197" width="246" height="10" rx="5" fill="{track}"/>
<rect x="604" y="197" width="{medium_width:.1f}" height="10" rx="5" fill="{medium}"/>
<text x="876" y="207" class="body" fill="{text}">{profile.medium}</text>

<text x="604" y="236" class="label" fill="{muted}">HARD</text>
<rect x="604" y="250" width="246" height="10" rx="5" fill="{track}"/>
<rect x="604" y="250" width="{hard_width:.1f}" height="10" rx="5" fill="{hard}"/>
<text x="876" y="260" class="body" fill="{text}">{profile.hard}</text>

<text x="604" y="294" class="label" fill="{muted}">LANGUAGES USED</text>
{chips}
</svg>'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--username", required=True)
    parser.add_argument("--light-output", type=Path)
    parser.add_argument("--dark-output", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    profile = fetch_profile(args.username)
    light_output = args.light_output or args.output
    if light_output is None:
        parser.error("--light-output or --output is required")
    dark_output = args.dark_output or light_output.with_name("leetcode-card-dark.svg")

    light_output.parent.mkdir(parents=True, exist_ok=True)
    dark_output.parent.mkdir(parents=True, exist_ok=True)
    light_output.write_text(render(profile, "light"), encoding="utf-8")
    dark_output.write_text(render(profile, "dark"), encoding="utf-8")


if __name__ == "__main__":
    main()
