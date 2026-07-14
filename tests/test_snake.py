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
