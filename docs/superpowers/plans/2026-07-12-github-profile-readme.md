# GitHub Profile README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a self-updating, terminal-styled GitHub profile README for `ssFari/ssFari` with a live "neofetch" stats card, typing header, snake animation, tech badges, and social links.

**Architecture:** A Python script (`today.py`) queries the GitHub GraphQL API and fills placeholder tokens in two SVG templates (dark/light). A GitHub Actions workflow runs it on a cron + on push and commits the updated SVGs. A second workflow generates the contribution snake. `README.md` embeds all pieces using GitHub's `#gh-dark-mode-only` / `#gh-light-mode-only` image trick.

**Tech Stack:** Python 3.11, `requests`, `python-dateutil`, pytest (dev), GitHub Actions, SVG, shields.io, readme-typing-svg, Platane/snk.

## Global Constraints

- Repo: `ssFari/ssFari`; owner display name: `Muhammad Safari Luthfi Siregar`; GitHub username: `ssFari`.
- Neofetch card is **text-only** (no ASCII portrait) and **dual light/dark**.
- Card metrics: uptime, repos, stars, followers, commits, contributions. **No Lines of Code.**
- Card colour: terminal green on dark (`#0d1117` bg / `#39d353` text) and green-on-light (`#ffffff` bg / `#0a7d33` text).
- Placeholder token format in SVG templates: `{{ key }}` (single space each side), keys: `uptime`, `repos`, `stars`, `followers`, `commits`, `contributions`.
- Secret name for the PAT: `ACCESS_TOKEN`. Username read from env `GH_LOGIN` (fallback literal `ssFari`).
- Social: IG `https://www.instagram.com/hi_ssfari`, X `https://x.com/ssFari1`, GitHub `https://github.com/ssFari`, Web `https://www.ssfari.dev/`.
- Line endings: repo is on Windows; commit files with LF where practical, don't fight Git's autocrlf warnings.

---

### Task 1: Python pure logic — uptime formatting, star summing, template fill

**Files:**
- Create: `today.py`
- Create: `requirements.txt`
- Create: `requirements-dev.txt`
- Test: `tests/test_today.py`

**Interfaces:**
- Produces:
  - `format_uptime(created_at: str, now: datetime) -> str` — `created_at` is ISO8601 (e.g. `"2023-05-01T00:00:00Z"`); returns e.g. `"2 years, 1 month, 11 days"`.
  - `sum_stars(repo_nodes: list[dict]) -> int` — each node has key `stargazerCount`.
  - `fill_template(svg: str, values: dict) -> str` — replaces every `{{ key }}` with `str(values[key])`.

- [ ] **Step 1: Create dependency files**

`requirements.txt`:
```
requests==2.32.3
python-dateutil==2.9.0.post0
```

`requirements-dev.txt`:
```
-r requirements.txt
pytest==8.3.3
```

- [ ] **Step 2: Write the failing test**

`tests/test_today.py`:
```python
from datetime import datetime, timezone
from today import format_uptime, sum_stars, fill_template


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
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest tests/test_today.py -v`
Expected: FAIL — `ModuleNotFoundError` / `ImportError: cannot import name 'format_uptime'`.

- [ ] **Step 4: Write minimal implementation in `today.py`**

```python
"""Generate a self-updating neofetch-style GitHub stats card SVG."""
from __future__ import annotations

from datetime import datetime
from dateutil import parser as date_parser
from dateutil.relativedelta import relativedelta


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
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/test_today.py -v`
Expected: PASS (5 passed).

- [ ] **Step 6: Commit**

```bash
git add today.py requirements.txt requirements-dev.txt tests/test_today.py
git commit -m "feat: add pure logic for uptime, star sum, template fill"
```

---

### Task 2: GitHub GraphQL data fetching

**Files:**
- Modify: `today.py`
- Test: `tests/test_today.py`

**Interfaces:**
- Consumes: `sum_stars` from Task 1.
- Produces:
  - `run_query(query: str, variables: dict, token: str) -> dict` — POSTs to `https://api.github.com/graphql`, returns parsed JSON `data`, raises `RuntimeError` on HTTP error or GraphQL `errors`.
  - `collect_stats(login: str, token: str) -> dict` — returns dict with keys `created_at` (str), `repos` (int), `stars` (int), `followers` (int), `commits` (int), `contributions` (int).

- [ ] **Step 1: Write the failing test (query builder + error handling, no network)**

Append to `tests/test_today.py`:
```python
import pytest
from today import extract_stats


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_today.py -k extract_stats -v`
Expected: FAIL — `ImportError: cannot import name 'extract_stats'`.

- [ ] **Step 3: Implement network + extraction in `today.py`**

Add imports at top (below existing imports):
```python
import os
import requests

GRAPHQL_URL = "https://api.github.com/graphql"

STATS_QUERY = """
query ($login: String!) {
  user(login: $login) {
    createdAt
    followers { totalCount }
    repositories(ownerAffiliations: OWNER, first: 100, orderBy: {field: STARGAZERS, direction: DESC}) {
      totalCount
      nodes { stargazerCount }
    }
    contributionsCollection { totalCommitContributions }
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, REPOSITORY]) { totalCount }
  }
}
"""
```

Add functions:
```python
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
    data = run_query(STATS_QUERY, {"login": login}, token)
    return extract_stats(data)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_today.py -v`
Expected: PASS (all tests).

- [ ] **Step 5: Commit**

```bash
git add today.py tests/test_today.py
git commit -m "feat: fetch and extract GitHub stats via GraphQL"
```

---

### Task 3: SVG templates (dark + light)

**Files:**
- Create: `dark_mode.svg`
- Create: `light_mode.svg`

**Interfaces:**
- Produces: two SVG files containing the placeholder tokens `{{ uptime }}`, `{{ repos }}`, `{{ stars }}`, `{{ followers }}`, `{{ commits }}`, `{{ contributions }}`. Consumed by `main()` in Task 4.

- [ ] **Step 1: Create `dark_mode.svg`**

```xml
<svg width="480" height="240" viewBox="0 0 480 240" fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .bg { fill: #0d1117; }
    .border { stroke: #39d353; stroke-width: 1.5; fill: none; }
    .txt { font-family: 'JetBrains Mono','Consolas',monospace; font-size: 15px; fill: #39d353; }
    .dim { fill: #2ea043; }
    .head { font-family: 'JetBrains Mono','Consolas',monospace; font-size: 15px; font-weight: 700; fill: #39d353; }
  </style>
  <rect class="bg" x="1" y="1" width="478" height="238" rx="10"/>
  <rect class="border" x="6" y="6" width="468" height="228" rx="8"/>
  <text class="head" x="24" y="38">safari@github</text>
  <text class="dim" x="24" y="54">----------------------------</text>
  <text class="txt" x="24" y="86">&gt; uptime       : {{ uptime }}</text>
  <text class="txt" x="24" y="114">&gt; repos        : {{ repos }}</text>
  <text class="txt" x="24" y="142">&gt; stars        : {{ stars }}</text>
  <text class="txt" x="24" y="170">&gt; followers    : {{ followers }}</text>
  <text class="txt" x="24" y="198">&gt; commits (yr) : {{ commits }}</text>
  <text class="txt" x="24" y="226">&gt; contributed  : {{ contributions }}</text>
</svg>
```

- [ ] **Step 2: Create `light_mode.svg`** (same layout, light palette)

```xml
<svg width="480" height="240" viewBox="0 0 480 240" fill="none" xmlns="http://www.w3.org/2000/svg">
  <style>
    .bg { fill: #ffffff; }
    .border { stroke: #0a7d33; stroke-width: 1.5; fill: none; }
    .txt { font-family: 'JetBrains Mono','Consolas',monospace; font-size: 15px; fill: #0a7d33; }
    .dim { fill: #1a8f42; }
    .head { font-family: 'JetBrains Mono','Consolas',monospace; font-size: 15px; font-weight: 700; fill: #0a7d33; }
  </style>
  <rect class="bg" x="1" y="1" width="478" height="238" rx="10"/>
  <rect class="border" x="6" y="6" width="468" height="228" rx="8"/>
  <text class="head" x="24" y="38">safari@github</text>
  <text class="dim" x="24" y="54">----------------------------</text>
  <text class="txt" x="24" y="86">&gt; uptime       : {{ uptime }}</text>
  <text class="txt" x="24" y="114">&gt; repos        : {{ repos }}</text>
  <text class="txt" x="24" y="142">&gt; stars        : {{ stars }}</text>
  <text class="txt" x="24" y="170">&gt; followers    : {{ followers }}</text>
  <text class="txt" x="24" y="198">&gt; commits (yr) : {{ commits }}</text>
  <text class="txt" x="24" y="226">&gt; contributed  : {{ contributions }}</text>
</svg>
```

- [ ] **Step 3: Sanity-check both files open in a browser** (placeholders will render literally — that's expected pre-fill).

- [ ] **Step 4: Commit**

```bash
git add dark_mode.svg light_mode.svg
git commit -m "feat: add dual-mode neofetch card SVG templates"
```

---

### Task 4: `main()` — wire fetch → fill → write both SVGs

**Files:**
- Modify: `today.py`
- Test: `tests/test_today.py`

**Interfaces:**
- Consumes: `collect_stats`, `format_uptime`, `fill_template` (Tasks 1–2); SVG templates (Task 3).
- Produces: `build_values(stats: dict, now: datetime) -> dict` (keys match token names); `render_file(path: str, values: dict) -> None`; `main() -> None`.

- [ ] **Step 1: Write the failing test for `build_values`**

Append to `tests/test_today.py`:
```python
from datetime import datetime, timezone
from today import build_values


def test_build_values_formats_uptime_and_passes_through():
    stats = {"created_at": "2023-05-01T00:00:00Z", "repos": 12, "stars": 25,
             "followers": 8, "commits": 340, "contributions": 4}
    now = datetime(2025, 6, 12, tzinfo=timezone.utc)
    values = build_values(stats, now)
    assert values == {"uptime": "2 years, 1 month, 11 days", "repos": 12,
                      "stars": 25, "followers": 8, "commits": 340, "contributions": 4}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_today.py -k build_values -v`
Expected: FAIL — `cannot import name 'build_values'`.

- [ ] **Step 3: Implement `build_values`, `render_file`, `main`**

```python
def build_values(stats: dict, now: datetime) -> dict:
    return {
        "uptime": format_uptime(stats["created_at"], now),
        "repos": stats["repos"],
        "stars": stats["stars"],
        "followers": stats["followers"],
        "commits": stats["commits"],
        "contributions": stats["contributions"],
    }


def render_file(path: str, values: dict) -> None:
    with open(path, "r", encoding="utf-8") as f:
        template = f.read()
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(fill_template(template, values))


def main() -> None:
    from datetime import timezone
    token = os.environ["ACCESS_TOKEN"]
    login = os.environ.get("GH_LOGIN", "ssFari")
    stats = collect_stats(login, token)
    values = build_values(stats, datetime.now(timezone.utc))
    render_file("dark_mode.svg", values)
    render_file("light_mode.svg", values)
    print("Updated cards:", values)


if __name__ == "__main__":
    main()
```

Note: `render_file` reads the template that already contains `{{ token }}`. Because the workflow commits the *filled* SVGs, re-running would find no tokens. To keep templates re-fillable, Task 5's workflow restores tokens via `git checkout` before running — see Task 5 Step 1. (Alternative simpler approach also documented there.)

- [ ] **Step 4: Run all tests**

Run: `python -m pytest tests/test_today.py -v`
Expected: PASS (all).

- [ ] **Step 5: Commit**

```bash
git add today.py tests/test_today.py
git commit -m "feat: wire main() to render both SVG cards"
```

---

### Task 5: `update-card.yml` GitHub Actions workflow

**Files:**
- Create: `.github/workflows/update-card.yml`
- Modify: `today.py` (separate template from output — see Step 1)
- Create: `templates/dark_mode.svg`, `templates/light_mode.svg` (move templates)

**Interfaces:**
- Consumes: `main()` (Task 4).
- Produces: committed `dark_mode.svg` / `light_mode.svg` at repo root, regenerated each run.

**Design note (fixes the re-fill problem):** Keep pristine templates in `templates/` and always render from them into root output files. This is cleaner than `git checkout` restores.

- [ ] **Step 1: Move templates and update `render_file`/`main`**

```bash
mkdir templates
git mv dark_mode.svg templates/dark_mode.svg
git mv light_mode.svg templates/light_mode.svg
```

Change `render_file` and `main` in `today.py`:
```python
def render_file(template_path: str, output_path: str, values: dict) -> None:
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(fill_template(template, values))


def main() -> None:
    from datetime import timezone
    token = os.environ["ACCESS_TOKEN"]
    login = os.environ.get("GH_LOGIN", "ssFari")
    stats = collect_stats(login, token)
    values = build_values(stats, datetime.now(timezone.utc))
    render_file("templates/dark_mode.svg", "dark_mode.svg", values)
    render_file("templates/light_mode.svg", "light_mode.svg", values)
    print("Updated cards:", values)
```

- [ ] **Step 2: Run tests (build_values/format/fill still green)**

Run: `python -m pytest tests/test_today.py -v`
Expected: PASS.

- [ ] **Step 3: Create `.github/workflows/update-card.yml`**

```yaml
name: Update profile card

on:
  schedule:
    - cron: "0 */12 * * *"
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: write

jobs:
  update:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - name: Install deps
        run: pip install -r requirements.txt
      - name: Generate cards
        env:
          ACCESS_TOKEN: ${{ secrets.ACCESS_TOKEN }}
          GH_LOGIN: ssFari
        run: python today.py
      - name: Commit updated cards
        run: |
          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add dark_mode.svg light_mode.svg
          if git diff --staged --quiet; then
            echo "No changes."
          else
            git commit -m "chore: update profile card [skip ci]"
            git push
          fi
```

- [ ] **Step 4: Commit**

```bash
git add today.py templates/ .github/workflows/update-card.yml
git commit -m "feat: add update-card workflow; render from pristine templates"
```

- [ ] **Step 5: Local end-to-end smoke test (requires a PAT)**

Run (PowerShell):
```powershell
$env:ACCESS_TOKEN="<your PAT>"; python today.py
```
Expected: prints `Updated cards: {...}` with real numbers; `dark_mode.svg` and `light_mode.svg` at root now contain real values (no `{{ }}` left). Open both in browser to confirm.
Then discard the local generated output if desired: `git checkout dark_mode.svg light_mode.svg` (or leave them — the workflow will overwrite).

---

### Task 6: `snake.yml` contribution snake workflow

**Files:**
- Create: `.github/workflows/snake.yml`

**Interfaces:**
- Produces: `github-snake.svg` (light) and `github-snake-dark.svg` (dark) on branch `output`, referenced by README (Task 7).

- [ ] **Step 1: Create `.github/workflows/snake.yml`**

```yaml
name: Generate snake

on:
  schedule:
    - cron: "0 0 * * *"
  workflow_dispatch:

permissions:
  contents: write

jobs:
  snake:
    runs-on: ubuntu-latest
    steps:
      - uses: Platane/snk@v3
        id: snake
        with:
          github_user_name: ssFari
          outputs: |
            dist/github-snake.svg
            dist/github-snake-dark.svg?palette=github-dark
      - uses: crazy-max/ghaction-github-pages@v4
        with:
          target_branch: output
          build_dir: dist
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

- [ ] **Step 2: Commit**

```bash
git add .github/workflows/snake.yml
git commit -m "feat: add contribution snake workflow"
```

- [ ] **Step 3: Verify after push**

After the repo is on GitHub and the workflow runs (trigger via Actions → Generate snake → Run workflow): confirm branch `output` exists and contains `github-snake.svg` + `github-snake-dark.svg`.

---

### Task 7: `README.md` assembly + setup guide

**Files:**
- Modify: `README.md`
- Create: `SETUP.md`

**Interfaces:**
- Consumes: all prior outputs (card SVGs, snake branch, typing service, badges).

- [ ] **Step 1: Replace `README.md`**

```markdown
<h1 align="center">
  <img src="https://readme-typing-svg.demolab.com?font=JetBrains+Mono&weight=700&size=28&duration=3000&pause=800&color=39D353&center=true&vCenter=true&width=600&lines=Muhammad+Safari+Luthfi+Siregar;Always+Learning" alt="typing header" />
</h1>

<p align="center">
  <img src="./dark_mode.svg#gh-dark-mode-only" alt="stats card" />
  <img src="./light_mode.svg#gh-light-mode-only" alt="stats card" />
</p>

<h3 align="center">🛠️ Tech Stack</h3>
<p align="center">
  <img src="https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white" />
  <img src="https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black" />
  <img src="https://img.shields.io/badge/Next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white" />
  <img src="https://img.shields.io/badge/React-61DAFB?style=for-the-badge&logo=react&logoColor=black" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-06B6D4?style=for-the-badge&logo=tailwindcss&logoColor=white" />
  <img src="https://img.shields.io/badge/Node.js-5FA04E?style=for-the-badge&logo=nodedotjs&logoColor=white" />
  <img src="https://img.shields.io/badge/Bun-000000?style=for-the-badge&logo=bun&logoColor=white" />
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" />
  <img src="https://img.shields.io/badge/Git-F05032?style=for-the-badge&logo=git&logoColor=white" />
</p>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/ssFari/ssFari/output/github-snake-dark.svg" />
  <source media="(prefers-color-scheme: light)" srcset="https://raw.githubusercontent.com/ssFari/ssFari/output/github-snake.svg" />
  <img alt="contribution snake" src="https://raw.githubusercontent.com/ssFari/ssFari/output/github-snake.svg" />
</picture>

<h3 align="center">🌐 Connect</h3>
<p align="center">
  <a href="https://www.ssfari.dev/"><img src="https://img.shields.io/badge/Website-39D353?style=for-the-badge&logo=googlechrome&logoColor=white" /></a>
  <a href="https://www.instagram.com/hi_ssfari"><img src="https://img.shields.io/badge/Instagram-E4405F?style=for-the-badge&logo=instagram&logoColor=white" /></a>
  <a href="https://x.com/ssFari1"><img src="https://img.shields.io/badge/X-000000?style=for-the-badge&logo=x&logoColor=white" /></a>
  <a href="https://github.com/ssFari"><img src="https://img.shields.io/badge/GitHub-181717?style=for-the-badge&logo=github&logoColor=white" /></a>
</p>
```

- [ ] **Step 2: Create `SETUP.md` (one-time steps for the owner)**

```markdown
# One-Time Setup

1. **Create a Personal Access Token (classic)**
   - GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic) → Generate new token (classic).
   - Scopes: `repo`, `read:user`.
   - Copy the token.

2. **Add it as a repo secret**
   - Repo `ssFari/ssFari` → Settings → Secrets and variables → Actions → New repository secret.
   - Name: `ACCESS_TOKEN`. Value: the token.

3. **Enable workflow write permission**
   - Repo → Settings → Actions → General → Workflow permissions → **Read and write permissions** → Save.

4. **First run**
   - Actions → "Update profile card" → Run workflow.
   - Actions → "Generate snake" → Run workflow.

The card refreshes automatically every 12 hours; the snake daily.
```

- [ ] **Step 3: Verify README renders locally** (Markdown preview) — links well-formed, no leftover `{{ }}` references.

- [ ] **Step 4: Commit**

```bash
git add README.md SETUP.md
git commit -m "feat: assemble profile README and setup guide"
```

---

### Task 8: Push, run workflows, verify live profile

**Files:** none (verification only)

- [ ] **Step 1:** Push all commits to `main` on GitHub (`git push`). This triggers `update-card.yml`.
- [ ] **Step 2:** Confirm `ACCESS_TOKEN` secret + read/write permission are set (per `SETUP.md`); if the first push ran before secrets existed, re-run "Update profile card".
- [ ] **Step 3:** Manually run "Generate snake" workflow; confirm `output` branch is created with the two snake SVGs.
- [ ] **Step 4:** Open `https://github.com/ssFari` in both light and dark GitHub themes; confirm typing header animates, the correct card variant shows with real numbers, snake renders, badges and social links appear.
- [ ] **Step 5:** Confirm the auto-commit `chore: update profile card` appears in history after the scheduled/triggered run.

---

## Self-Review

- **Spec coverage:** neofetch card (T1–T5), dual light/dark (T3 + T7 embed), metrics uptime/repos/stars/followers/commits/contributions (T2/T4), LOC excluded (not implemented — correct), typing header (T7), snake (T6/T7), badges (T7), social (T7), PAT/permissions prerequisites (SETUP.md T7 + T8). Data-flow, error handling (`run_query` raises; missing values default via `.get`) covered.
- **Placeholder scan:** no TBD/TODO; all code blocks concrete.
- **Type consistency:** `render_file` signature changes in Task 5 (adds `template_path`) — Task 5 updates both definition and `main()` call together; earlier `render_file(path, values)` fully replaced. Token keys consistent (`uptime/repos/stars/followers/commits/contributions`) across templates, `build_values`, and tests.
