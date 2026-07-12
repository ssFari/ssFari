"""Generate a self-updating neofetch-style GitHub stats card SVG."""
from __future__ import annotations

import os
from datetime import datetime, timezone

import requests
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta

GRAPHQL_URL = "https://api.github.com/graphql"

STATS_QUERY = """
query ($login: String!, $cursor: String) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, first: 100, after: $cursor, orderBy: {field: STARGAZERS, direction: DESC}) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes { stargazerCount }
    }
    contributionsCollection { totalCommitContributions }
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]) { totalCount }
  }
}
"""


def format_uptime(created_at: str, now: datetime) -> str:
    created = date_parser.isoparse(created_at)
    delta = relativedelta(now, created)

    def unit(value: int, name: str) -> str:
        return f"{value} {name}" if value == 1 else f"{value} {name}s"

    return f"{unit(delta.years, 'year')}, {unit(delta.months, 'month')}, {unit(delta.days, 'day')}"


def sum_stars(repo_nodes: list[dict]) -> int:
    return sum(node.get("stargazerCount", 0) for node in repo_nodes)


def fill_template(svg: str, values: dict) -> str:
    out = svg
    for key, value in values.items():
        out = out.replace("{{ " + key + " }}", str(value))
    return out


def run_query(query: str, variables: dict, token: str) -> dict:
    resp = requests.post(
        GRAPHQL_URL,
        json={"query": query, "variables": variables},
        headers={"Authorization": f"bearer {token}"},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"GraphQL request failed: {resp.status_code} {resp.text}")
    payload = resp.json()
    if "errors" in payload:
        raise RuntimeError(f"GraphQL errors: {payload['errors']}")
    return payload["data"]


def extract_stats(data: dict) -> dict:
    user = data["user"]
    return {
        "created_at": user["createdAt"],
        "repos": user["repositories"]["totalCount"],
        "stars": sum_stars(user["repositories"]["nodes"]),
        "followers": user["followers"]["totalCount"],
        "commits": user["contributionsCollection"]["totalCommitContributions"],
        "contributions": user["repositoriesContributedTo"]["totalCount"],
    }


def collect_stats(login: str, token: str) -> dict:
    data = run_query(STATS_QUERY, {"login": login, "cursor": None}, token)
    stats = extract_stats(data)
    # Sum stars across ALL owned repos, not just the first page of 100.
    page = data["user"]["repositories"]["pageInfo"]
    while page["hasNextPage"]:
        data = run_query(STATS_QUERY, {"login": login, "cursor": page["endCursor"]}, token)
        repos = data["user"]["repositories"]
        stats["stars"] += sum_stars(repos["nodes"])
        page = repos["pageInfo"]
    return stats


def build_values(stats: dict, now: datetime) -> dict:
    return {
        "uptime": format_uptime(stats["created_at"], now),
        "repos": stats["repos"],
        "stars": stats["stars"],
        "followers": stats["followers"],
        "commits": stats["commits"],
        "contributions": stats["contributions"],
    }


def render_file(template_path: str, output_path: str, values: dict) -> None:
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(fill_template(template, values))


def main() -> None:
    token = os.environ["ACCESS_TOKEN"]
    login = os.environ.get("GH_LOGIN", "ssFari")
    stats = collect_stats(login, token)
    values = build_values(stats, datetime.now(timezone.utc))
    render_file("templates/dark_mode.svg", "dark_mode.svg", values)
    render_file("templates/light_mode.svg", "light_mode.svg", values)
    print("Updated cards:", values)


if __name__ == "__main__":
    main()
