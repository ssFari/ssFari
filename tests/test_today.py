from datetime import datetime, timezone
from today import (
    format_uptime,
    sum_stars,
    fill_template,
    extract_stats,
    build_values,
)


def test_format_uptime_years_months_days():
    now = datetime(2025, 6, 12, tzinfo=timezone.utc)
    assert format_uptime("2023-05-01T00:00:00Z", now) == "2 years, 1 month, 11 days"


def test_format_uptime_singular_units():
    now = datetime(2024, 6, 2, tzinfo=timezone.utc)
    assert format_uptime("2023-05-01T00:00:00Z", now) == "1 year, 1 month, 1 day"


def test_format_uptime_zero_days_omitted_when_only_days_zero():
    now = datetime(2024, 5, 1, tzinfo=timezone.utc)
    assert format_uptime("2023-05-01T00:00:00Z", now) == "1 year, 0 months, 0 days"


def test_sum_stars():
    nodes = [{"stargazerCount": 3}, {"stargazerCount": 0}, {"stargazerCount": 12}]
    assert sum_stars(nodes) == 15


def test_fill_template_replaces_all_tokens():
    svg = "<text>{{ repos }}</text><text>{{ stars }}</text>"
    out = fill_template(svg, {"repos": 12, "stars": 25})
    assert out == "<text>12</text><text>25</text>"


def test_extract_stats_maps_graphql_payload():
    data = {
        "user": {
            "createdAt": "2023-05-01T00:00:00Z",
            "followers": {"totalCount": 8},
            "repositories": {
                "totalCount": 12,
                "nodes": [{"stargazerCount": 10}, {"stargazerCount": 15}],
            },
            "contributionsCollection": {"totalCommitContributions": 340},
            "repositoriesContributedTo": {"totalCount": 4},
        }
    }
    stats = extract_stats(data)
    assert stats == {
        "created_at": "2023-05-01T00:00:00Z",
        "repos": 12,
        "stars": 25,
        "followers": 8,
        "commits": 340,
        "contributions": 4,
    }


def test_extract_stats_missing_values_default_to_zero():
    data = {"user": {"createdAt": "2023-05-01T00:00:00Z",
                     "followers": {"totalCount": 0},
                     "repositories": {"totalCount": 0, "nodes": []},
                     "contributionsCollection": {"totalCommitContributions": 0},
                     "repositoriesContributedTo": {"totalCount": 0}}}
    stats = extract_stats(data)
    assert stats["stars"] == 0
    assert stats["repos"] == 0


def test_build_values_formats_uptime_and_passes_through():
    stats = {"created_at": "2023-05-01T00:00:00Z", "repos": 12, "stars": 25,
             "followers": 8, "commits": 340, "contributions": 4}
    now = datetime(2025, 6, 12, tzinfo=timezone.utc)
    values = build_values(stats, now)
    assert values == {"uptime": "2 years, 1 month, 11 days", "repos": 12,
                      "stars": 25, "followers": 8, "commits": 340, "contributions": 4}
