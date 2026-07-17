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


def test_build_path_zigzag_visits_all_once():
    grid = [[0] * 7 for _ in range(3)]  # 3 columns, 7 rows
    path = snake.build_path(grid)
    assert len(path) == 21
    assert len(set(path)) == 21          # unik semua
    assert path[0] == (0, 0)
    assert path[6] == (0, 6)             # kolom 0 turun 0->6
    assert path[7] == (1, 6)             # kolom 1 mulai dari bawah
    assert path[13] == (1, 0)            # kolom 1 naik 6->0
    assert path[14] == (2, 0)            # kolom 2 turun lagi


def test_snake_length_grows_per_eat_then_caps():
    assert snake.snake_length(0, 0) == 1
    assert snake.snake_length(5, 3) == 4
    assert snake.snake_length(100, 50, max_len=16) == 16


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
    assert snake.THEMES["light"]["empty"] in svg     # empty tema light
    assert snake.THEMES["light"]["levels"][1] in svg  # level-1 kontras


def test_render_svg_empty_contributions_head_only():
    import xml.etree.ElementTree as ET
    grid = [[0] * 7 for _ in range(4)]
    tl = snake.build_timeline(snake.build_path(grid), grid)
    svg = snake.render_svg(grid, tl, "dark")
    ET.fromstring(svg)
    assert tl["eat_events"] == []
    assert svg.count('rx="3"') == 1


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
    # keyframe sel berakhir kembali ke warna level (grafik permanen)
    start = svg.index("@keyframes cell_0_1{")
    body = svg[start:svg.index("}", svg.index("100%", start))]
    assert snake.THEMES["dark"]["levels"][1] in body  # warna level-1 dark
    assert snake.THEMES["dark"]["empty"] in body      # sempat meredup (dip)


def test_render_svg_cell_flash_is_transient_not_held():
    # Grafik selalu tampil: sel hanya meredup SEKALI (dip transien) saat
    # dimakan, tidak ditahan kosong sampai reset (yang bikin warna hilang lama).
    grid = [[0, 1, 0, 0, 0, 0, 0]]
    tl = snake.build_timeline(snake.build_path(grid), grid)
    svg = snake.render_svg(grid, tl, "dark")
    start = svg.index("@keyframes cell_0_1{")
    body = svg[start:svg.index("}}", start) + 2]     # blok keyframe utuh
    empty = snake.THEMES["dark"]["empty"]
    assert body.count(f"fill:{empty};") == 1          # dip sekali, bukan ditahan


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


def test_no_teleport_between_frames_before_reset():
    grid = [[(c + r) % 4 + 1 for r in range(7)] for c in range(6)]
    path = snake.build_path(grid)
    tl = snake.build_timeline(path, grid)
    frames = tl["frames"][:tl["reset_start"]]
    for a, b in zip(frames, frames[1:]):
        (c1, r1), (c2, r2) = a["cell"], b["cell"]
        assert max(abs(c1 - c2), abs(r1 - r2)) <= 1
