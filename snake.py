"""Generate an animated contribution-snake SVG that grows as it eats."""
from __future__ import annotations

import os

from today import run_query

CELL = 11
GAP = 2
STEP_MS = 60
MAX_LEN = 16

LEVEL_MAP = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

CALENDAR_QUERY = """
query ($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays { contributionLevel weekday }
        }
      }
    }
  }
}
"""


def fetch_calendar(login: str, token: str) -> list[dict]:
    data = run_query(CALENDAR_QUERY, {"login": login}, token)
    cal = data["user"]["contributionsCollection"]["contributionCalendar"]
    return cal["weeks"]


def build_grid(weeks: list[dict]) -> list[list[int]]:
    grid = []
    for week in weeks:
        col = [0] * 7
        for day in week["contributionDays"]:
            col[day["weekday"]] = LEVEL_MAP.get(day["contributionLevel"], 0)
        grid.append(col)
    return grid


def build_path(grid: list[list[int]]) -> list[tuple[int, int]]:
    path = []
    for c in range(len(grid)):
        rows = range(7) if c % 2 == 0 else range(6, -1, -1)
        for r in rows:
            path.append((c, r))
    return path


def snake_length(step: int, eaten: int, max_len: int = MAX_LEN) -> int:
    return min(eaten + 1, max_len)


def build_timeline(path, grid, max_len: int = MAX_LEN) -> dict:
    levels = [grid[c][r] for (c, r) in path]
    eat_steps = [i for i, lv in enumerate(levels) if lv > 0]
    return {
        "steps": len(path),
        "cells": path,
        "levels": levels,
        "eat_steps": eat_steps,
        "max_len": max_len,
    }


THEMES = {
    "dark": {
        "empty": "#0d1b2a",
        "levels": ["#0d1b2a", "#1e3a5f", "#2e5480", "#4a7ab5", "#6ea3e0"],
        "head": "#8ab4f0",
    },
    "light": {
        "empty": "#e5e7eb",
        "levels": ["#e5e7eb", "#c3ccd6", "#9aa7b5", "#6b7a8c", "#3d4b5a"],
        "head": "#3d4b5a",
    },
}


def _xy(cell: tuple[int, int]) -> tuple[int, int]:
    c, r = cell
    return c * (CELL + GAP), r * (CELL + GAP)


def render_svg(grid: list[list[int]], timeline: dict, theme: str) -> str:
    t = THEMES[theme]
    cols = len(grid)
    width = cols * (CELL + GAP) - GAP
    height = 7 * (CELL + GAP) - GAP
    steps = timeline["steps"]
    path = timeline["cells"]
    levels = timeline["levels"]
    eat_steps = timeline["eat_steps"]
    max_len = timeline["max_len"]
    dur = steps * STEP_MS
    denom = max(steps - 1, 1)

    style = ["<style>"]
    style.append(f".cell{{width:{CELL}px;height:{CELL}px;}}")
    # eaten fade per level
    for lv in range(1, 5):
        style.append(
            f"@keyframes eat{lv}{{from{{fill:{t['levels'][lv]};}}"
            f"to{{fill:{t['empty']};}}}}"
        )
    # shared move keyframes
    move = "".join(
        f"{i / denom * 100:.3f}%{{transform:translate({_xy(c)[0]}px,{_xy(c)[1]}px);}}"
        for i, c in enumerate(path)
    )
    style.append("@keyframes move{" + move + "}")
    # shared swallow (color) keyframes
    swallow = "".join(
        f"{i / denom * 100:.3f}%{{fill:{t['levels'][lv]};}}"
        for i, lv in enumerate(levels)
    )
    style.append("@keyframes swallow{" + swallow + "}")
    # per-segment growth (appear at eat time)
    for k in range(max_len):
        if k == 0:
            appear = 0.0
        elif k - 1 < len(eat_steps):
            appear = eat_steps[k - 1] / denom * 100
        else:
            break
        op = max(0.2, 1 - k * 0.05)
        nxt = min(appear + 0.001, 100)
        style.append(
            f"@keyframes grow{k}{{0%{{opacity:0;}}{appear:.3f}%{{opacity:0;}}"
            f"{nxt:.3f}%{{opacity:{op};}}100%{{opacity:{op};}}}}"
        )
    style.append("</style>")

    parts = [
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
        "".join(style),
    ]

    # contribution cells
    for i, c in enumerate(path):
        lv = levels[i]
        x, y = _xy(c)
        if lv > 0:
            parts.append(
                f'<rect class="cell" rx="2" x="{x}" y="{y}" '
                f'style="fill:{t["levels"][lv]};'
                f'animation:eat{lv} 400ms linear {i * STEP_MS}ms forwards;"/>'
            )
        else:
            parts.append(
                f'<rect class="cell" rx="2" x="{x}" y="{y}" '
                f'style="fill:{t["empty"]};"/>'
            )

    # snake segments
    for k in range(max_len):
        if k > 0 and k - 1 >= len(eat_steps):
            break
        delay = k * STEP_MS
        anims = [f"move {dur}ms linear {delay}ms infinite",
                 f"grow{k} {dur}ms linear infinite"]
        fill = t["head"]
        if k > 0:
            anims.insert(1, f"swallow {dur}ms linear {delay}ms infinite")
            fill = t["empty"]
        parts.append(
            f'<rect class="cell" rx="3" x="0" y="0" '
            f'style="fill:{fill};opacity:0;animation:{",".join(anims)};"/>'
        )

    parts.append("</svg>")
    return "".join(parts)


def _write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content)


def main() -> None:
    token = os.environ["ACCESS_TOKEN"]
    login = os.environ.get("GH_LOGIN", "ssFari")
    weeks = fetch_calendar(login, token)
    grid = build_grid(weeks)
    timeline = build_timeline(build_path(grid), grid)
    _write("dist/github-snake-dark.svg", render_svg(grid, timeline, "dark"))
    _write("dist/github-snake.svg", render_svg(grid, timeline, "light"))
    print(f"Generated snake for {login}: {timeline['steps']} cells, "
          f"{len(timeline['eat_steps'])} contributions")


if __name__ == "__main__":
    main()
