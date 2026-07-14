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
