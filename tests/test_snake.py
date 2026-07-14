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
