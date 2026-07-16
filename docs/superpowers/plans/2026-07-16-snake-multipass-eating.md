# Snake Multi-Pass Eating + Loop Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ubah `snake.py` agar ular memakan kontribusi **terkecil dulu lalu terbesar** (multi-pass per level) dan animasinya **loop mulus dengan reset** (sel tumbuh kembali, ular menyusut), menggantikan perilaku sekali-jalan yang membuat grid kosong permanen.

**Architecture:** Tulis ulang `build_timeline` jadi model multi-pass berbasis daftar `frames` (satu sapuan per level yang ada, + fase reset), lalu tulis ulang `render_svg` agar `@keyframes` posisi/warna/opacity/sel bersumber dari `frames` dan semua animasi `infinite` yang sinkron. `build_path`, `today.py`, `snake.yml`, dan tema tidak berubah.

**Tech Stack:** Python 3.11, pytest, SVG + CSS `@keyframes` (self-contained).

## Global Constraints

- Tema warna **tetap** (jangan ubah `THEMES`): dark `empty=#0d1b2a` levels `[#0d1b2a,#1e3a5f,#2e5480,#4a7ab5,#6ea3e0]` head `#8ab4f0`; light `empty=#e5e7eb` levels `[#e5e7eb,#c3ccd6,#9aa7b5,#6b7a8c,#3d4b5a]` head `#3d4b5a`.
- `build_path` (zig-zag kronologis) **tidak berubah**.
- `today.py`, `.github/workflows/snake.yml` **tidak disentuh**.
- Warna badan lewat **satu** timeline `swallow` bersama + `animation-delay` per segmen (file-light, dukung total makanan >16 via sliding window). Bukan warna fix per rect.
- Jumlah sapuan = **hanya level yang ada** di grid (`present_levels`); grid kosong tetap satu sapuan.
- TDD: test dulu (RED) → implementasi minimal (GREEN) → commit tiap task.
- Output test harus bersih (tanpa warning).
- Jalankan test dari root repo: `python -m pytest tests/test_snake.py -v`.

---

## File Structure

- Modify: `snake.py` — konstanta (`STEP_MS`, `RESET_FRAMES`), `build_timeline` (rewrite), `render_svg` (rewrite). `fetch_calendar`, `build_grid`, `build_path`, `snake_length`, `_xy`, `_write`, `main`, `THEMES` tetap.
- Modify: `tests/test_snake.py` — ganti test `build_timeline`/`render_svg` lama ke model baru; tambah test multi-pass, loop-reset, dan guard ukuran/durasi.

---

### Task 1: Multi-pass `build_timeline` + render port (loop belum reset)

Rewrite `build_timeline` ke model `frames`, dan port `render_svg` agar konsumsi kunci baru sambil tetap menghasilkan SVG valid (sel masih `forwards` — loop-reset diperbaiki di Task 2). Semua test hijau di akhir task.

**Files:**
- Modify: `snake.py:8-11` (konstanta), `snake.py:65-74` (`build_timeline`), `snake.py:96-185` (`render_svg`)
- Test: `tests/test_snake.py`

**Interfaces:**
- Consumes: `build_path(grid) -> list[tuple[int,int]]`, `grid: list[list[int]]` (kolom×7, nilai level 0–4), `THEMES`.
- Produces:
  - Konstanta: `STEP_MS = 30`, `RESET_FRAMES = 40`.
  - `build_timeline(path, grid, max_len=MAX_LEN) -> dict` dengan kunci:
    - `frames: list[dict]` — tiap `{"cell": (int,int), "is_eat": bool, "food_level": int|None}`
    - `total: int` = `len(frames)`
    - `eat_events: list[dict]` — tiap `{"frame": int, "cell": (int,int), "level": int}`, terurut naik per level
    - `present_levels: list[int]` — level >0 yang ada, terurut
    - `reset_start: int` — indeks frame awal fase reset
    - `max_len: int`
  - `render_svg(grid, timeline, theme) -> str` — SVG valid; rect sel `rx="2"`, segmen ular `rx="3"`; keyframe `move` & `swallow` ada.
  - `snake_length(step, eaten, max_len=MAX_LEN)` **tidak berubah**.

- [ ] **Step 1: Tulis test build_timeline multi-pass (RED)**

Ganti test lama `test_build_timeline_aligns_levels_and_eats` (baris 59–71) dengan blok berikut, dan tambahkan test empty-grid. Sisakan `test_snake_length_grows_per_eat_then_caps` apa adanya.

```python
def test_build_timeline_multipass_present_levels():
    grid = [[0, 1, 0, 0, 0, 0, 0], [0, 0, 0, 2, 0, 0, 0], [0, 0, 0, 0, 0, 0, 2]]
    path = snake.build_path(grid)
    tl = snake.build_timeline(path, grid)
    assert tl["present_levels"] == [1, 2]
    assert tl["total"] == len(path) * 2 + snake.RESET_FRAMES
    assert tl["reset_start"] == len(path) * 2
    assert tl["max_len"] == 16


def test_build_timeline_eats_only_target_level_per_pass():
    grid = [[0, 1, 0, 0, 0, 0, 0], [0, 0, 0, 2, 0, 0, 0]]
    path = snake.build_path(grid)
    tl = snake.build_timeline(path, grid)
    pass_len = len(path)
    pass0 = tl["frames"][:pass_len]
    pass1 = tl["frames"][pass_len:2 * pass_len]
    assert [f["cell"] for f in pass0 if f["is_eat"]] == [(0, 1)]
    assert [f["cell"] for f in pass1 if f["is_eat"]] == [(1, 3)]
    # sel level-2 dilewati (tidak dimakan) selama pass level-1
    assert all(not f["is_eat"] for f in pass0 if f["cell"] == (1, 3))


def test_build_timeline_eat_events_ordered_small_to_large():
    grid = [[0, 2, 0, 1, 0, 0, 0]]  # level-2 di atas level-1 pada kolom sama
    path = snake.build_path(grid)
    tl = snake.build_timeline(path, grid)
    assert [ev["level"] for ev in tl["eat_events"]] == [1, 2]
    assert tl["eat_events"][0]["cell"] == (0, 3)  # level-1 dimakan lebih dulu
    assert tl["eat_events"][1]["cell"] == (0, 1)  # level-2 belakangan
    assert tl["eat_events"][0]["frame"] < tl["eat_events"][1]["frame"]


def test_build_timeline_empty_grid_sweeps_once_no_eats():
    grid = [[0] * 7 for _ in range(3)]
    path = snake.build_path(grid)
    tl = snake.build_timeline(path, grid)
    assert tl["present_levels"] == []
    assert tl["eat_events"] == []
    assert tl["total"] == len(path) + snake.RESET_FRAMES
    assert tl["reset_start"] == len(path)
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_snake.py::test_build_timeline_multipass_present_levels -v`
Expected: FAIL (`AttributeError: module 'snake' has no attribute 'RESET_FRAMES'` atau `KeyError`).

- [ ] **Step 3: Tambah konstanta + rewrite build_timeline**

Di `snake.py`, ubah blok konstanta (baris 8–11):

```python
CELL = 11
GAP = 2
STEP_MS = 30
MAX_LEN = 16
RESET_FRAMES = 40
```

Ganti seluruh `build_timeline` (baris 65–74) dengan:

```python
def build_timeline(path, grid, max_len: int = MAX_LEN) -> dict:
    lookup = {(c, r): grid[c][r] for c in range(len(grid)) for r in range(7)}
    present_levels = sorted({lv for col in grid for lv in col if lv > 0})
    sweep_levels = present_levels or [0]  # grid kosong: satu sapuan tanpa makan

    frames = []
    for level in sweep_levels:
        for cell in path:
            is_eat = level > 0 and lookup[cell] == level
            frames.append({
                "cell": cell,
                "is_eat": is_eat,
                "food_level": level if is_eat else None,
            })
    reset_start = len(frames)
    last = path[-1] if path else (0, 0)
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
```

- [ ] **Step 4: Jalankan test build_timeline, pastikan lulus**

Run: `python -m pytest tests/test_snake.py -k build_timeline -v`
Expected: 4 PASS. (Test `render_svg` masih akan gagal — diperbaiki di step berikut.)

- [ ] **Step 5: Update test render_svg ke interface baru (RED)**

Ganti tiga test render lama (`test_render_svg_is_wellformed_and_themed` baris 74–87, `test_render_svg_light_theme_uses_gray` baris 90–94, `test_render_svg_empty_contributions_head_only` baris 97–104) dengan:

```python
def test_render_svg_is_wellformed_and_themed():
    import xml.etree.ElementTree as ET
    grid = [[0, 1, 0, 2, 0, 3, 0], [4, 0, 1, 0, 2, 0, 3]]
    tl = snake.build_timeline(snake.build_path(grid), grid)
    svg = snake.render_svg(grid, tl, "dark")
    ET.fromstring(svg)
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    assert "@keyframes move" in svg
    assert "@keyframes swallow" in svg
    assert "#0d1b2a" in svg
    assert "{{" not in svg
    n_cells = sum(len(col) for col in grid)
    assert svg.count('rx="2"') == n_cells
    assert svg.count('rx="3"') == min(16, len(tl["eat_events"]) + 1)


def test_render_svg_light_theme_uses_gray():
    grid = [[1, 0, 0, 0, 0, 0, 0]]
    tl = snake.build_timeline(snake.build_path(grid), grid)
    svg = snake.render_svg(grid, tl, "light")
    assert "#e5e7eb" in svg


def test_render_svg_empty_contributions_head_only():
    import xml.etree.ElementTree as ET
    grid = [[0] * 7 for _ in range(4)]
    tl = snake.build_timeline(snake.build_path(grid), grid)
    svg = snake.render_svg(grid, tl, "dark")
    ET.fromstring(svg)
    assert tl["eat_events"] == []
    assert svg.count('rx="3"') == 1
```

Run: `python -m pytest tests/test_snake.py -k render_svg -v`
Expected: FAIL (`render_svg` masih baca kunci lama `steps`/`cells`/`levels`/`eat_steps` → `KeyError`).

- [ ] **Step 6: Rewrite render_svg (port ke frames; sel masih forwards)**

Ganti seluruh `render_svg` (baris 96–185) dengan:

```python
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

    # eaten fade per level (interim: forwards, diganti loop di Task 2)
    for lv in range(1, 5):
        style.append(
            f"@keyframes eat{lv}{{from{{fill:{t['levels'][lv]};}}"
            f"to{{fill:{t['empty']};}}}}"
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

    # grow{k}: opacity per segmen (muncul saat makan ke-k)
    for k in range(n_segments):
        op = max(0.2, 1 - k * 0.05)
        appear = 0.0 if k == 0 else min(pct(eat_events[k - 1]["frame"]), 99.9)
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

    # sel kontribusi
    for c in range(cols):
        for r in range(7):
            lv = grid[c][r]
            x, y = _xy((c, r))
            if lv > 0:
                ef = eat_frame[(c, r)]
                parts.append(
                    f'<rect class="cell" rx="2" x="{x}" y="{y}" '
                    f'style="fill:{t["levels"][lv]};'
                    f'animation:eat{lv} 400ms linear {ef * STEP_MS}ms forwards;"/>'
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
```

- [ ] **Step 7: Jalankan seluruh suite, pastikan hijau**

Run: `python -m pytest tests/test_snake.py -v`
Expected: semua PASS, output bersih.

- [ ] **Step 8: Commit**

```bash
git add snake.py tests/test_snake.py
git commit -m "feat: multi-pass snake eating (smallest level first)"
```

---

### Task 2: Loop reset — sel tumbuh kembali + ular menyusut

Ganti sel `forwards` dengan keyframe **loop penuh** per sel (fade-out saat dimakan → tumbuh kembali di fase reset), dan buat segmen badan **opacity→0 di fase reset** sehingga ular menyusut ke kepala lalu loop mulus.

**Files:**
- Modify: `snake.py` `render_svg` (bagian keyframe `eat{lv}`→`cell_{c}_{r}`, `grow{k}`, dan style sel)
- Test: `tests/test_snake.py`

**Interfaces:**
- Consumes: `build_timeline(...)` dari Task 1 (butuh `reset_start`).
- Produces: `render_svg` tanpa `forwards`; keyframe `@keyframes cell_{c}_{r}` per sel kontribusi (kembali ke warna level di 100%); segmen badan (k≥1) berakhir `opacity:0`.

- [ ] **Step 1: Tulis test loop-reset (RED)**

Tambahkan di `tests/test_snake.py`:

```python
def test_render_svg_cells_loop_not_forwards():
    grid = [[0, 1, 0, 2, 0, 0, 0]]
    tl = snake.build_timeline(snake.build_path(grid), grid)
    svg = snake.render_svg(grid, tl, "dark")
    assert "forwards" not in svg            # sel regrow, bukan sekali jalan
    assert "@keyframes cell_" in svg        # keyframe loop per sel
    assert "animation:cell_0_1" in svg      # sel level-1 dipakai


def test_render_svg_snake_shrinks_at_reset():
    grid = [[0, 1, 0, 2, 0, 0, 0]]
    tl = snake.build_timeline(snake.build_path(grid), grid)
    svg = snake.render_svg(grid, tl, "dark")
    # segmen badan berakhir opacity 0 -> ular menyusut ke kepala saat reset
    assert "100%{opacity:0;}" in svg


def test_render_svg_cell_keyframe_returns_to_level_color():
    grid = [[0, 1, 0, 0, 0, 0, 0]]
    tl = snake.build_timeline(snake.build_path(grid), grid)
    svg = snake.render_svg(grid, tl, "dark")
    # keyframe sel berakhir kembali ke warna level (loop refill)
    start = svg.index("@keyframes cell_0_1{")
    body = svg[start:svg.index("}", svg.index("100%", start))]
    assert "#1e3a5f" in body                # warna level-1 dark
    assert "#0d1b2a" in body                # sempat jadi empty (termakan)
```

- [ ] **Step 2: Jalankan test, pastikan gagal**

Run: `python -m pytest tests/test_snake.py -k "loop_not_forwards or shrinks or returns_to_level" -v`
Expected: FAIL (`forwards` masih ada; `@keyframes cell_` belum ada).

- [ ] **Step 3: Ganti keyframe eat{lv} → cell_{c}_{r} (loop penuh)**

Di `render_svg`, hapus blok pembuat `@keyframes eat{lv}`:

```python
    # eaten fade per level (interim: forwards, diganti loop di Task 2)
    for lv in range(1, 5):
        style.append(
            f"@keyframes eat{lv}{{from{{fill:{t['levels'][lv]};}}"
            f"to{{fill:{t['empty']};}}}}"
        )
```

dan ganti dengan pembuat keyframe per sel (butuh `reset_start` + `reset_pct`). Sisipkan tepat setelah baris `style = ["<style>", ...]` dan definisi `reset_pct`:

```python
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
```

- [ ] **Step 4: Buat grow{k} menyusut di reset + kepala tetap tampil**

Ganti loop `grow{k}` (versi Task 1) dengan:

```python
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
```

- [ ] **Step 5: Ubah rect sel agar pakai animasi loop-nya**

Ganti cabang `if lv > 0:` di bagian render sel kontribusi dengan:

```python
            if lv > 0:
                parts.append(
                    f'<rect class="cell" rx="2" x="{x}" y="{y}" '
                    f'style="fill:{t["levels"][lv]};'
                    f'animation:cell_{c}_{r} {dur}ms linear infinite;"/>'
                )
```

- [ ] **Step 6: Jalankan seluruh suite, pastikan hijau**

Run: `python -m pytest tests/test_snake.py -v`
Expected: semua PASS (termasuk 3 test baru), output bersih.

- [ ] **Step 7: Commit**

```bash
git add snake.py tests/test_snake.py
git commit -m "feat: seamless loop reset — cells regrow, snake shrinks"
```

---

### Task 3: Guard ukuran & durasi (verifikasi skala penuh)

Tambah test yang me-render grid padat realistis (53 minggu, semua level) untuk menjaga SVG well-formed, tercap 16 segmen, ukuran wajar, dan durasi loop terbatas.

**Files:**
- Test: `tests/test_snake.py`

**Interfaces:**
- Consumes: `build_timeline`, `render_svg`, `STEP_MS` dari Task 1–2.
- Produces: dua test guard (tidak mengubah `snake.py` kecuali tuning konstanta bila guard gagal).

- [ ] **Step 1: Tulis test guard (RED/verifikasi)**

Tambahkan di `tests/test_snake.py`:

```python
def _dense_grid():
    # 53 minggu, tiap sel punya kontribusi mencakup keempat level
    return [[(c + r) % 4 + 1 for r in range(7)] for c in range(53)]


def test_render_svg_dense_grid_wellformed_and_capped():
    import xml.etree.ElementTree as ET
    grid = _dense_grid()
    tl = snake.build_timeline(snake.build_path(grid), grid)
    svg = snake.render_svg(grid, tl, "dark")
    ET.fromstring(svg)
    assert tl["present_levels"] == [1, 2, 3, 4]
    assert svg.count('rx="3"') == 16          # segmen tercap
    assert len(svg) < 400_000                 # anggaran ukuran


def test_render_svg_loop_duration_bounded():
    grid = _dense_grid()
    tl = snake.build_timeline(snake.build_path(grid), grid)
    dur_ms = tl["total"] * snake.STEP_MS
    assert dur_ms <= 60_000                    # loop <= 60 dtk kasus terburuk
```

- [ ] **Step 2: Jalankan test guard**

Run: `python -m pytest tests/test_snake.py -k "dense_grid or duration_bounded" -v`
Expected: PASS. Jika `len(svg)` ≥ 400k atau `dur_ms` > 60k, turunkan `STEP_MS` / kompres stop `move` yang berulang (dedup transform berturut identik) lalu ulangi — jangan longgarkan angka guard tanpa alasan.

- [ ] **Step 3: Jalankan seluruh suite penuh**

Run: `python -m pytest tests/test_snake.py -v`
Expected: semua PASS, output bersih.

- [ ] **Step 4: Render sintetis manual (sanity, tanpa token)**

Run:
```bash
python -c "import snake; g=[[(c+r)%4+1 for r in range(7)] for c in range(53)]; tl=snake.build_timeline(snake.build_path(g),g); s=snake.render_svg(g,tl,'dark'); open('scratch-snake.svg','w',encoding='utf-8').write(s); print(len(s),'bytes', tl['total'],'frames', tl['present_levels'])"
```
Expected: cetak ukuran byte < 400000, jumlah frame, dan `[1, 2, 3, 4]`. Buka `scratch-snake.svg` bila ingin verifikasi visual, lalu hapus (`git status` harus bersih; jangan commit file scratch).

- [ ] **Step 5: Commit**

```bash
git add tests/test_snake.py
git commit -m "test: guard SVG size and loop duration at full scale"
```

---

## Self-Review

**Spec coverage:**
- Multi-pass per level → Task 1 (`build_timeline`, `test_build_timeline_eats_only_target_level_per_pass`). ✓
- Pass hanya level yang ada → Task 1 (`present_levels`, `test_..._present_levels`). ✓
- Terkecil→terbesar (skip yang besar saat pass kecil) → Task 1 (`test_..._ordered_small_to_large`, `test_..._eats_only_target_level_per_pass`). ✓
- Tumbuh carry-over cap 16 → `snake_length` (tetap) + `grow{k}` di `eat_events` kumulatif; cap `n_segments=min(16,…)` diuji `test_render_svg_dense_grid_wellformed_and_capped`. ✓
- Warna badan via swallow bersama + delay → Task 1 render (`@keyframes swallow`, diuji `test_render_svg_is_wellformed_and_themed`). ✓
- Fase reset: sel tumbuh kembali + ular menyusut → Task 2 (`cell_{c}_{r}`, `grow0` kepala tetap, body→0; diuji `test_render_svg_cells_loop_not_forwards`, `_snake_shrinks_at_reset`, `_cell_keyframe_returns_to_level_color`). ✓
- Loop mulus (bukan forwards) → Task 2 (`assert "forwards" not in svg`). ✓
- Pacing ~20–30 dtk / STEP_MS turun → Task 1 (`STEP_MS=30`) + Task 3 guard durasi. ✓
- Grid kosong tidak crash, sapuan sekali → Task 1 (`test_build_timeline_empty_grid_sweeps_once_no_eats`, `test_render_svg_empty_contributions_head_only`). ✓
- Dua tema → `test_render_svg_light_theme_uses_gray`. ✓
- Ukuran wajar → Task 3 guard. ✓
- `build_path`/`today.py`/`snake.yml`/`THEMES` tak berubah → tidak ada task menyentuhnya. ✓

**Placeholder scan:** tidak ada TBD/TODO; semua step memuat kode/keyframe konkret. ✓

**Type consistency:** kunci `frames`/`total`/`eat_events`/`present_levels`/`reset_start`/`max_len` konsisten dipakai lintas Task 1–3; `eat_events[k]["frame"]/["cell"]/["level"]` konsisten; `cell_{c}_{r}` dinamai sama di keyframe & rect. ✓
