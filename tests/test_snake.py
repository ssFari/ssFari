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
