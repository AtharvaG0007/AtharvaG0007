#!/usr/bin/env python3
"""
Generate an animated Pac-Man contribution graph from GitHub contributions.
This script fetches GitHub contribution data via the GraphQL API and writes SVG files.

A valid GitHub token must be supplied in the GITHUB_TOKEN environment variable.
"""

import os
import sys
from pathlib import Path

import requests

GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "AtharvaG0007")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_API = "https://api.github.com/graphql"
REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "assets"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)


def get_contributions_data():
    """Fetch user's contribution data from the GitHub GraphQL API."""
    if not GITHUB_TOKEN:
        raise RuntimeError(
            "GITHUB_TOKEN is required. Set it in the environment before running this script."
        )

    query = """
    query($userName:String!) {
      user(login: $userName) {
        contributionsCollection {
          contributionCalendar {
            totalContributions
            weeks {
              contributionDays {
                contributionCount
                date
              }
            }
          }
        }
      }
    }
    """

    variables = {"userName": GITHUB_USERNAME}
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Content-Type": "application/json",
        "Accept": "application/vnd.github+json",
        "User-Agent": "pacman-contribution-graph",
    }

    # Retry transient API/network failures; fail clearly on auth or GraphQL errors.
    last_error = None
    for attempt in range(3):
        try:
            response = requests.post(
                GITHUB_API,
                json={"query": query, "variables": variables},
                headers=headers,
                timeout=30,
            )
            if response.status_code in (429, 500, 502, 503, 504):
                last_error = f"GitHub API returned HTTP {response.status_code}: {response.text[:500]}"
                if attempt < 2:
                    import time
                    time.sleep(2 ** attempt)
                    continue
            response.raise_for_status()
            payload = response.json()
            break
        except requests.RequestException as exc:
            last_error = str(exc)
            if attempt < 2:
                import time
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"Failed to fetch GitHub contribution data after 3 attempts: {last_error}") from exc
        except ValueError as exc:
            raise RuntimeError("GitHub API returned invalid JSON.") from exc
    else:
        raise RuntimeError(f"GitHub API request failed after 3 attempts: {last_error}")

    if response.status_code == 403:
        raise RuntimeError(
            "GitHub API returned 403. Check that GITHUB_TOKEN is available and the token has not exceeded its API rate limit. "
            f"Response: {response.text[:500]}"
        )

    if "errors" in payload:
        raise RuntimeError(f"GitHub GraphQL error: {payload['errors']}")

    user = payload.get("data", {}).get("user")
    if user is None:
        raise RuntimeError(f"No GitHub user found for login '{GITHUB_USERNAME}'.")

    weeks = (
        user.get("contributionsCollection", {})
        .get("contributionCalendar", {})
        .get("weeks")
    )
    if not isinstance(weeks, list) or not weeks:
        raise RuntimeError("GitHub contribution calendar did not return any weeks.")

    return weeks


def contributions_to_grid(weeks):
    """Convert weekly contribution data to a 7x52 grid."""
    grid = [[0] * len(weeks) for _ in range(7)]

    for week_idx, week in enumerate(weeks):
        if not isinstance(week, dict):
            raise ValueError(f"Invalid contribution week at index {week_idx}: expected an object.")
        contribution_days = week.get("contributionDays", [])
        if not isinstance(contribution_days, list):
            raise ValueError(f"Invalid contributionDays at week {week_idx}: expected a list.")
        for day_idx, day in enumerate(contribution_days[:7]):
            if not isinstance(day, dict):
                raise ValueError(f"Invalid contribution day at week {week_idx}, day {day_idx}.")
            grid[day_idx][week_idx] = int(day.get("contributionCount", 0))

    return grid


def get_contribution_color(count, dark_mode=False):
    """Map contribution count to color."""
    if dark_mode:
        if count == 0:
            return "#0e1117"
        elif count < 5:
            return "#0f3e1e"
        elif count < 10:
            return "#00a651"
        elif count < 20:
            return "#26a641"
        else:
            return "#39d353"
    else:
        if count == 0:
            return "#ebedf0"
        elif count < 5:
            return "#c6e48b"
        elif count < 10:
            return "#7bc96f"
        elif count < 20:
            return "#239a3b"
        else:
            return "#196c2e"


def create_pacman_svg(grid, dark_mode=False):
    """Generate SVG with animated Pac-Man and contribution graph."""
    cell_size = 12
    padding = 20
    gap = 2

    rows = len(grid)
    cols = len(grid[0]) if grid else 0

    width = cols * (cell_size + gap) + padding * 2 + 80
    height = rows * (cell_size + gap) + padding * 2 + 60

    bg_color = "#0d1117" if dark_mode else "#ffffff"
    text_color = "#c9d1d9" if dark_mode else "#1f2937"

    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        "<defs>",
        "<style>",
        "rect.contribution { transition: opacity 0.3s; cursor: pointer; }",
        "rect.contribution:hover { opacity: 0.7; }",
        "@keyframes pacman-move {",
        "  0% { transform: translateX(0); }",
        "  50% { transform: translateX(30px); }",
        "  100% { transform: translateX(0); }",
        "}",
        "@keyframes pacman-mouth {",
        "  0% { clip-path: polygon(50% 0%, 50% 0%, 50% 100%, 50% 100%); }",
        "  25% { clip-path: polygon(50% 20%, 80% 50%, 50% 80%, 20% 50%); }",
        "  50% { clip-path: polygon(50% 0%, 50% 0%, 50% 100%, 50% 100%); }",
        "  75% { clip-path: polygon(50% 20%, 80% 50%, 50% 80%, 20% 50%); }",
        "  100% { clip-path: polygon(50% 0%, 50% 0%, 50% 100%, 50% 100%); }",
        "}",
        ".pacman { animation: pacman-move 3s ease-in-out infinite; }",
        ".pacman-body { animation: pacman-mouth 0.6s ease-in-out infinite; }",
        "</style>",
        "</defs>",
        f'<rect width="100%" height="100%" fill="{bg_color}"/>',
        f'<text x="{padding}" y="35" font-family="Arial, sans-serif" font-size="18" font-weight="bold" fill="{text_color}">@{GITHUB_USERNAME} Contributions</text>',
    ]

    y_offset = padding + 50
    x_offset = padding

    for col_idx in range(cols):
        for row_idx in range(rows):
            count = grid[row_idx][col_idx] if col_idx < len(grid[row_idx]) else 0
            color = get_contribution_color(count, dark_mode)
            x = x_offset + col_idx * (cell_size + gap)
            y = y_offset + row_idx * (cell_size + gap)

            svg_lines.append(
                f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" '
                f'fill="{color}" class="contribution" rx="1" ry="1" '
                f'title="Contributions: {count}"/>'
            )

    pacman_x = x_offset + cols * (cell_size + gap) + 40
    pacman_y = y_offset + (rows * (cell_size + gap)) / 2

    svg_lines.extend([
        f'<g class="pacman" transform="translate({pacman_x}, {pacman_y})">',
        f'<circle cx="0" cy="0" r="10" fill="#FFD700" class="pacman-body"/>',
        f'<circle cx="4" cy="-3" r="1.5" fill="{bg_color}"/>',
        "</g>",
        "<!-- Pellets -->",
    ])

    for i in range(3):
        pellet_x = pacman_x - 30 + (i * 15)
        pellet_y = pacman_y
        svg_lines.append(f'<circle cx="{pellet_x}" cy="{pellet_y}" r="2" fill="#FFD700" opacity="0.6"/>')

    svg_lines.append("</svg>")
    return "\n".join(svg_lines)


def main():
    """Main execution function."""
    print(f"Generating Pac-Man contribution graph for {GITHUB_USERNAME}...")

    try:
        weeks = get_contributions_data()
    except Exception as exc:  # noqa: BLE001
        print(f"Failed to fetch contribution data: {exc}")
        print("Aborting graph generation to avoid publishing incorrect contribution data.")
        sys.exit(1)

    grid = contributions_to_grid(weeks)

    svg_dark = create_pacman_svg(grid, dark_mode=True)
    svg_light = create_pacman_svg(grid, dark_mode=False)

    dark_path = OUTPUT_DIR / "pacman-contribution-graph-dark.svg"
    light_path = OUTPUT_DIR / "pacman-contribution-graph.svg"

    with open(dark_path, "w", encoding="utf-8") as handle:
        handle.write(svg_dark)
    print(f"✓ Dark mode graph generated: {dark_path}")

    with open(light_path, "w", encoding="utf-8") as handle:
        handle.write(svg_light)
    print(f"✓ Light mode graph generated: {light_path}")


if __name__ == "__main__":
    main()
