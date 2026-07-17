"""Generate an animated contribution-snake SVG that grows as it eats."""
from __future__ import annotations

import os

from today import run_query

CELL = 11
GAP = 2
STEP_MS = 20
MAX_LEN = 16
RESET_FRAMES = 40

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
    lookup = {(c, r): grid[c][r] for c in range(len(grid)) for r in range(7)}
    present_levels = sorted({lv for col in grid for lv in col if lv > 0})
    sweep_levels = present_levels or [0]  # grid kosong: satu sapuan tanpa makan

    frames = []
    for pass_index, level in enumerate(sweep_levels):
        # boustrophedon: balik arah sapuan berselang agar kepala mengalir
        # kontinu tanpa teleport di batas antar-pass
        ordered = path if pass_index % 2 == 0 else list(reversed(path))
        for cell in ordered:
            is_eat = level > 0 and lookup[cell] == level
            frames.append({
                "cell": cell,
                "is_eat": is_eat,
                "food_level": level if is_eat else None,
            })
    reset_start = len(frames)
    last = frames[-1]["cell"] if frames else (0, 0)
    frames.extend(
        {"cell": last, "is_eat": False, "food_level": None}
        for _ in range(RESET_FRAMES)
    )
    eat_events = [
        {"frame": i, "cell": f["cell"], "level": f["food_level"]}
        for i, f in enumerate(frames)
        if f["is_eat"]
    ]
    return {
        "frames": frames,
        "total": len(frames),
        "eat_events": eat_events,
        "present_levels": present_levels,
        "reset_start": reset_start,
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
    frames = timeline["frames"]
    total = timeline["total"]
    eat_events = timeline["eat_events"]
    max_len = timeline["max_len"]
    denom = max(total - 1, 1)
    dur = total * STEP_MS

    def pct(i: int) -> float:
        return i / denom * 100

    eat_frame = {ev["cell"]: ev["frame"] for ev in eat_events}
    n_segments = min(max_len, len(eat_events) + 1)

    style = ["<style>", f".cell{{width:{CELL}px;height:{CELL}px;}}"]

    reset_start = timeline["reset_start"]
    reset_pct = pct(reset_start)

    # keyframe loop per sel kontribusi: warna -> (saat dimakan) empty ->
    # (fase reset) tumbuh kembali ke warna level
    for c in range(cols):
        for r in range(7):
            lv = grid[c][r]
            if lv <= 0:
                continue
            ef = eat_frame[(c, r)]
            ep = pct(ef)
            ep2 = min(ep + 0.4, 99.9)
            rp2 = min(reset_pct + 0.4, 100)
            color = t["levels"][lv]
            empty = t["empty"]
            style.append(
                f"@keyframes cell_{c}_{r}{{0%{{fill:{color};}}"
                f"{ep:.3f}%{{fill:{color};}}{ep2:.3f}%{{fill:{empty};}}"
                f"{reset_pct:.3f}%{{fill:{empty};}}{rp2:.3f}%{{fill:{color};}}"
                f"100%{{fill:{color};}}}}"
            )

    # move: posisi melintasi seluruh frames (multi-pass + reset)
    move = "".join(
        f"{pct(i):.3f}%{{transform:translate({_xy(f['cell'])[0]}px,"
        f"{_xy(f['cell'])[1]}px);}}"
        for i, f in enumerate(frames)
    )
    style.append("@keyframes move{" + move + "}")

    # swallow: warna makanan piecewise-constant yang dibawa turun badan
    swallow_stops = []
    cur = None
    for i, f in enumerate(frames):
        if f["is_eat"]:
            cur = f["food_level"]
        color = t["levels"][cur] if cur else t["empty"]
        swallow_stops.append(f"{pct(i):.3f}%{{fill:{color};}}")
    style.append("@keyframes swallow{" + "".join(swallow_stops) + "}")

    # grow{k}: opacity per segmen — muncul saat makan ke-k, menyusut saat reset
    for k in range(n_segments):
        op = max(0.2, 1 - k * 0.05)
        if k == 0:
            # kepala: tampil sepanjang loop (ular menyusut ke 1 segmen)
            style.append(
                f"@keyframes grow0{{0%{{opacity:{op};}}"
                f"{reset_pct:.3f}%{{opacity:{op};}}100%{{opacity:{op};}}}}"
            )
            continue
        appear = min(pct(eat_events[k - 1]["frame"]), 99.9)
        nxt = min(appear + 0.001, 100)
        style.append(
            f"@keyframes grow{k}{{0%{{opacity:0;}}{appear:.3f}%{{opacity:0;}}"
            f"{nxt:.3f}%{{opacity:{op};}}{reset_pct:.3f}%{{opacity:{op};}}"
            f"100%{{opacity:0;}}}}"
        )
    style.append("</style>")

    parts = [
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">',
        "".join(style),
    ]

    # sel kontribusi
    for c in range(cols):
        for r in range(7):
            lv = grid[c][r]
            x, y = _xy((c, r))
            if lv > 0:
                parts.append(
                    f'<rect class="cell" rx="2" x="{x}" y="{y}" '
                    f'style="fill:{t["levels"][lv]};'
                    f'animation:cell_{c}_{r} {dur}ms linear infinite;"/>'
                )
            else:
                parts.append(
                    f'<rect class="cell" rx="2" x="{x}" y="{y}" '
                    f'style="fill:{t["empty"]};"/>'
                )

    # segmen ular
    for k in range(n_segments):
        delay = k * STEP_MS
        anims = [f"move {dur}ms linear {delay}ms infinite both",
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
    print(f"Generated snake for {login}: {timeline['total']} frames, "
          f"{len(timeline['eat_events'])} contributions")


if __name__ == "__main__":
    main()
