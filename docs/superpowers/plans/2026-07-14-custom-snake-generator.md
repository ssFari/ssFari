# Custom Contribution-Snake Generator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ganti `Platane/snk` dengan generator Python custom yang melahap grafik kontribusi asli, badan ular tumbuh saat makan, dan warna badan mengikuti warna makanan.

**Architecture:** `snake.py` mem-fetch `contributionCalendar` via GraphQL (reuse `run_query` dari `today.py`), menyusun grid 7×N, menghitung jalur sapuan kronologis, lalu me-render satu SVG self-contained per tema dengan animasi CSS `@keyframes`. Semua segmen ular berbagi keyframes gerak/warna yang sama (beda `animation-delay`) agar file ringan; opacity per-segmen mengikat pertumbuhan ke event makan.

**Tech Stack:** Python 3.11, `requests` (via `today.run_query`), pytest. Tanpa dependency baru.

## Global Constraints

- Bahasa: Python; konsisten dengan `today.py`. Reuse `run_query` dari `today.py` (jangan duplikasi POST GraphQL).
- Tanpa dependency baru di luar yang sudah ada (`requests`, `python-dateutil`, `pytest`).
- TDD: tulis test dulu, lihat gagal, implementasi minimal, lihat lulus, commit.
- Tulis file output dengan `newline="\n"` (ikuti pola `render_file` di `today.py`).
- SVG self-contained (nol dependency eksternal, animasi CSS inline).
- Dua tema: dark = navy, light = gray (nilai warna verbatim di Task 5).
- Konstanta: `CELL=11`, `GAP=2`, `STEP_MS=60`, `MAX_LEN=16`.
- Level map GitHub: `NONE=0, FIRST_QUARTILE=1, SECOND_QUARTILE=2, THIRD_QUARTILE=3, FOURTH_QUARTILE=4`.
- Windows: warning `LF will be replaced by CRLF` bersifat kosmetik — abaikan.

---

### Task 1: Fetch calendar + konstanta modul

**Files:**
- Create: `snake.py`
- Test: `tests/test_snake.py`

**Interfaces:**
- Consumes: `today.run_query(query: str, variables: dict, token: str) -> dict`
- Produces:
  - Konstanta modul: `CELL`, `GAP`, `STEP_MS`, `MAX_LEN`, `LEVEL_MAP`, `CALENDAR_QUERY`
  - `fetch_calendar(login: str, token: str) -> list[dict]` — mengembalikan list `weeks`, tiap elemen `{"contributionDays": [{"contributionLevel": str, "weekday": int}, ...]}`

- [ ] **Step 1: Tulis test yang gagal**

```python
# tests/test_snake.py
import snake


def test_fetch_calendar_returns_weeks(monkeypatch):
    fake = {
        "user": {
            "contributionsCollection": {
                "contributionCalendar": {
                    "weeks": [
                        {"contributionDays": [
                            {"contributionLevel": "NONE", "weekday": 0},
                            {"contributionLevel": "FOURTH_QUARTILE", "weekday": 1},
                        ]},
                    ]
                }
            }
        }
    }
    monkeypatch.setattr(snake, "run_query", lambda q, v, t: fake)
    weeks = snake.fetch_calendar("ssFari", "tok")
    assert len(weeks) == 1
    assert weeks[0]["contributionDays"][1]["contributionLevel"] == "FOURTH_QUARTILE"
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_snake.py::test_fetch_calendar_returns_weeks -v`
Expected: FAIL (`AttributeError: module 'snake' has no attribute ...` / ImportError)

- [ ] **Step 3: Implementasi minimal**

```python
# snake.py
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
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_snake.py::test_fetch_calendar_returns_weeks -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add snake.py tests/test_snake.py
git commit -m "feat: add snake calendar fetch and module constants"
```

---

### Task 2: build_grid

**Files:**
- Modify: `snake.py`
- Test: `tests/test_snake.py`

**Interfaces:**
- Consumes: `LEVEL_MAP`, `weeks` dari `fetch_calendar`
- Produces: `build_grid(weeks: list[dict]) -> list[list[int]]` — kolom; `grid[c] = [level_r0..level_r6]`, hari hilang dipad `0`

- [ ] **Step 1: Tulis test yang gagal**

```python
def test_build_grid_pads_and_maps_levels():
    weeks = [
        {"contributionDays": [
            {"contributionLevel": "NONE", "weekday": 0},
            {"contributionLevel": "SECOND_QUARTILE", "weekday": 3},
        ]},
        {"contributionDays": [
            {"contributionLevel": "FOURTH_QUARTILE", "weekday": 6},
        ]},
    ]
    grid = snake.build_grid(weeks)
    assert len(grid) == 2
    assert grid[0] == [0, 0, 0, 2, 0, 0, 0]
    assert grid[1] == [0, 0, 0, 0, 0, 0, 4]
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_snake.py::test_build_grid_pads_and_maps_levels -v`
Expected: FAIL (`AttributeError: build_grid`)

- [ ] **Step 3: Implementasi minimal**

```python
def build_grid(weeks: list[dict]) -> list[list[int]]:
    grid = []
    for week in weeks:
        col = [0] * 7
        for day in week["contributionDays"]:
            col[day["weekday"]] = LEVEL_MAP.get(day["contributionLevel"], 0)
        grid.append(col)
    return grid
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_snake.py::test_build_grid_pads_and_maps_levels -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add snake.py tests/test_snake.py
git commit -m "feat: build 7xN contribution grid from weeks"
```

---

### Task 3: build_path (sapuan kronologis)

**Files:**
- Modify: `snake.py`
- Test: `tests/test_snake.py`

**Interfaces:**
- Consumes: `grid` dari `build_grid`
- Produces: `build_path(grid: list[list[int]]) -> list[tuple[int, int]]` — urutan `(col, row)` zig-zag, mengunjungi tiap sel tepat sekali

- [ ] **Step 1: Tulis test yang gagal**

```python
def test_build_path_zigzag_visits_all_once():
    grid = [[0] * 7 for _ in range(3)]  # 3 kolom
    path = snake.build_path(grid)
    assert len(path) == 21
    assert len(set(path)) == 21          # unik semua
    assert path[0] == (0, 0)
    assert path[6] == (0, 6)             # kolom 0 turun 0->6
    assert path[7] == (1, 6)             # kolom 1 mulai dari bawah
    assert path[13] == (1, 0)            # kolom 1 naik 6->0
    assert path[14] == (2, 0)            # kolom 2 turun lagi
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_snake.py::test_build_path_zigzag_visits_all_once -v`
Expected: FAIL (`AttributeError: build_path`)

- [ ] **Step 3: Implementasi minimal**

```python
def build_path(grid: list[list[int]]) -> list[tuple[int, int]]:
    path = []
    for c in range(len(grid)):
        rows = range(7) if c % 2 == 0 else range(6, -1, -1)
        for r in rows:
            path.append((c, r))
    return path
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_snake.py::test_build_path_zigzag_visits_all_once -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add snake.py tests/test_snake.py
git commit -m "feat: chronological zig-zag sweep path"
```

---

### Task 4: snake_length + build_timeline

**Files:**
- Modify: `snake.py`
- Test: `tests/test_snake.py`

**Interfaces:**
- Consumes: `grid`, `path`, `MAX_LEN`
- Produces:
  - `snake_length(step: int, eaten: int, max_len: int = MAX_LEN) -> int` — panjang = `min(eaten + 1, max_len)`
  - `build_timeline(path, grid, max_len=MAX_LEN) -> dict` dengan kunci: `steps: int`, `cells: list[tuple]`, `levels: list[int]`, `eat_steps: list[int]`, `max_len: int`

- [ ] **Step 1: Tulis test yang gagal**

```python
def test_snake_length_grows_per_eat_then_caps():
    assert snake.snake_length(0, 0) == 1
    assert snake.snake_length(5, 3) == 4
    assert snake.snake_length(100, 50, max_len=16) == 16


def test_build_timeline_aligns_levels_and_eats():
    grid = [[0, 1, 0, 0, 0, 0, 0], [0, 0, 0, 2, 0, 0, 0]]
    path = snake.build_path(grid)
    tl = snake.build_timeline(path, grid, max_len=16)
    assert tl["steps"] == 14
    assert tl["cells"] == path
    assert tl["levels"][path.index((0, 1))] == 1
    assert tl["levels"][path.index((1, 3))] == 2
    # eat_steps = indeks langkah di sel berisi kontribusi
    assert tl["eat_steps"] == sorted(
        [path.index((0, 1)), path.index((1, 3))]
    )
    assert tl["max_len"] == 16
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_snake.py -k "snake_length or build_timeline" -v`
Expected: FAIL (`AttributeError`)

- [ ] **Step 3: Implementasi minimal**

```python
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
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_snake.py -k "snake_length or build_timeline" -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add snake.py tests/test_snake.py
git commit -m "feat: snake growth timeline tied to eat events"
```

---

### Task 5: render_svg + THEMES

**Files:**
- Modify: `snake.py`
- Test: `tests/test_snake.py`

**Interfaces:**
- Consumes: `grid`, `timeline` (output Task 4), `CELL`, `GAP`, `STEP_MS`
- Produces:
  - `THEMES: dict` (kunci `"dark"`, `"light"`; tiap tema `{"empty": str, "levels": list[str] (5), "head": str}`)
  - `render_svg(grid: list[list[int]], timeline: dict, theme: str) -> str` — string SVG self-contained

**Catatan render:** Semua segmen ular pakai `@keyframes move` (posisi) & `@keyframes swallow` (warna) yang sama, beda `animation-delay = k*STEP_MS` (segmen ke-k tertinggal k langkah). Pertumbuhan diikat ke makan lewat `@keyframes grow{k}`: segmen k mulai tampak saat food ke-k dimakan (`eat_steps[k-1]`). Kepala (k=0) warna aksen, tak ikut `swallow`. Sel berisi memudar via `@keyframes eat{level}`.

- [ ] **Step 1: Tulis test yang gagal (smoke)**

```python
def test_render_svg_is_wellformed_and_themed():
    grid = [[0, 1, 0, 2, 0, 3, 0], [4, 0, 1, 0, 2, 0, 3]]
    tl = snake.build_timeline(snake.build_path(grid), grid)
    svg = snake.render_svg(grid, tl, "dark")
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    assert "@keyframes move" in svg
    assert "@keyframes swallow" in svg
    assert "#0d1b2a" in svg            # warna tema dark
    assert "{{" not in svg              # nol placeholder
    # jumlah rect sel = 14, plus segmen ular (<= MAX_LEN)
    assert svg.count("<rect") >= 14


def test_render_svg_light_theme_uses_gray():
    grid = [[1, 0, 0, 0, 0, 0, 0]]
    tl = snake.build_timeline(snake.build_path(grid), grid)
    svg = snake.render_svg(grid, tl, "light")
    assert "#e5e7eb" in svg
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_snake.py -k render_svg -v`
Expected: FAIL (`AttributeError: render_svg`)

- [ ] **Step 3: Implementasi minimal**

```python
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
```

- [ ] **Step 4: Jalankan test, pastikan lulus**

Run: `python -m pytest tests/test_snake.py -k render_svg -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add snake.py tests/test_snake.py
git commit -m "feat: render animated growing-snake SVG with CSS keyframes"
```

---

### Task 6: main() — tulis dua tema

**Files:**
- Modify: `snake.py`

**Interfaces:**
- Consumes: env `ACCESS_TOKEN`, opsional `GH_LOGIN` (default `"ssFari"`); semua fungsi di atas
- Produces: menulis `dist/github-snake-dark.svg` & `dist/github-snake.svg`

- [ ] **Step 1: Implementasi (tanpa test unit — I/O + env)**

```python
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
```

- [ ] **Step 2: Verifikasi seluruh test lulus**

Run: `python -m pytest -q`
Expected: semua test lulus (test lama `today` + test baru `snake`)

- [ ] **Step 3: Commit**

```bash
git add snake.py
git commit -m "feat: snake main writes dark and light SVGs to dist"
```

---

### Task 7: Ganti workflow snake.yml → snake.py

**Files:**
- Modify: `.github/workflows/snake.yml`

**Interfaces:**
- Consumes: `snake.py main()`, secret `ACCESS_TOKEN`
- Produces: branch `output` berisi `github-snake.svg` & `github-snake-dark.svg` hasil generator custom

- [ ] **Step 1: Ganti isi snake.yml**

Ganti seluruh blok `jobs:` menjadi (hapus penggunaan `Platane/snk`):

```yaml
name: Generate snake

on:
  schedule:
    - cron: "0 0 * * *"
  workflow_dispatch:
  push:
    branches: [main]
    paths:
      - "snake.py"
      - ".github/workflows/snake.yml"

permissions:
  contents: write

jobs:
  snake:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: python snake.py
        env:
          ACCESS_TOKEN: ${{ secrets.ACCESS_TOKEN }}
          GH_LOGIN: ssFari
      - uses: crazy-max/ghaction-github-pages@v4
        with:
          target_branch: output
          build_dir: dist
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

- [ ] **Step 2: Validasi YAML lokal**

Run: `python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/snake.yml')); print('yaml ok')"`
Expected: `yaml ok`

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/snake.yml
git commit -m "ci: run custom snake.py instead of Platane/snk"
```

---

### Task 8: Verifikasi end-to-end

**Files:** none (verifikasi)

- [ ] **Step 1: Generate lokal untuk inspeksi visual**

Jalankan generator dengan token nyata (owner menjalankan; jangan hardcode token):

```bash
ACCESS_TOKEN=<pat> GH_LOGIN=ssFari python snake.py
```
Expected: terbentuk `dist/github-snake-dark.svg` & `dist/github-snake.svg`; output print jumlah cells & kontribusi.

- [ ] **Step 2: Buka kedua SVG di browser**

Verifikasi visual: ular menyapu kiri→kanan urut waktu, badan memanjang saat melewati kontribusi, warna makanan mengalir di badan, ekor lebih pudar, loop mulus. Dark = navy, light = gray. Jika timing/opacity perlu tuning, sesuaikan `STEP_MS`/faktor opacity di `snake.py` lalu ulang.

- [ ] **Step 3: Push & jalankan workflow**

```bash
git push origin main
```
Lalu trigger workflow `Generate snake` (via `gh workflow run "Generate snake"` atau tab Actions), tunggu hijau, cek branch `output` ter-update. README `<picture>` sudah menunjuk ke sana (tidak berubah).

- [ ] **Step 4: Verifikasi di profil**

Buka `github.com/ssFari` (mode terang & gelap), hard-refresh (camo cache). Pastikan ular animasi custom tampil sesuai kriteria sukses spec.

---

## Self-Review

**Spec coverage:** fetch kontribusi asli (T1), grid toleran (T2), sapuan kronologis (T3), tumbuh-per-makan + cap + timeline (T4), warna-menelan + ekor pudar + dua tema + render (T5), tulis dua file (T6), ganti Platane/snk (T7), error handling (reuse `run_query` yang raise pada gagal → workflow gagal & `output` lama dipertahankan; kontribusi kosong → `eat_steps` kosong, ular tetap render; token hilang → `KeyError` eksplisit), testing (T1–T5). Semua bagian spec tercakup.

**Placeholder scan:** tidak ada TBD/TODO; semua step berisi kode nyata.

**Type consistency:** `fetch_calendar→list[dict]` dipakai `build_grid`; `build_grid→list[list[int]]` dipakai `build_path`/`build_timeline`; `build_timeline→dict` (kunci `steps/cells/levels/eat_steps/max_len`) dipakai `render_svg`; nama fungsi konsisten lintas tugas.
