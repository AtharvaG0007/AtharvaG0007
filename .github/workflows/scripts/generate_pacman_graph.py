#!/usr/bin/env python3
import requests
import os
from datetime import datetime, timedelta
from pathlib import Path

GITHUB_USERNAME = os.getenv('GITHUB_USERNAME', 'AtharvaG0007')
GITHUB_API = "https://api.github.com/graphql"
OUTPUT_DIR = Path('assets')

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def get_contributions_data():
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
    try:
        response = requests.post(GITHUB_API, json={"query": query, "variables": variables}, timeout=10)
        response.raise_for_status()
        data = response.json()
        if 'errors' in data:
            print(f"GraphQL Error: {data['errors']}")
            return None
        return data['data']['user']['contributionsCollection']['contributionCalendar']['weeks']
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None

def contributions_to_grid(weeks):
    grid = [[0] * len(weeks) for _ in range(7)]
    for week_idx, week in enumerate(weeks):
        for day_idx, day in enumerate(week['contributionDays']):
            grid[day_idx][week_idx] = day['contributionCount']
    return grid

def get_contribution_color(count, dark_mode=False):
    if dark_mode:
        if count == 0:
            return '#0e1117'
        elif count < 5:
            return '#0f3e1e'
        elif count < 10:
            return '#00a651'
        elif count < 20:
            return '#26a641'
        else:
            return '#39d353'
    else:
        if count == 0:
            return '#ebedf0'
        elif count < 5:
            return '#c6e48b'
        elif count < 10:
            return '#7bc96f'
        elif count < 20:
            return '#239a3b'
        else:
            return '#196c2e'

def create_pacman_svg(grid, dark_mode=False):
    cell_size = 12
    padding = 20
    gap = 2
    rows = len(grid)
    cols = len(grid[0]) if grid else 0
    width = cols * (cell_size + gap) + padding * 2 + 80
    height = rows * (cell_size + gap) + padding * 2 + 60
    bg_color = '#0d1117' if dark_mode else '#ffffff'
    text_color = '#c9d1d9' if dark_mode else '#1f2937'
    
    svg_lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<defs>',
        '<style>',
        'rect.contribution { transition: opacity 0.3s; cursor: pointer; }',
        'rect.contribution:hover { opacity: 0.7; }',
        '@keyframes pacman-move { 0% { transform: translateX(0); } 50% { transform: translateX(30px); } 100% { transform: translateX(0); } }',
        '@keyframes pacman-mouth { 0% { clip-path: polygon(50% 0%, 50% 0%, 50% 100%, 50% 100%); } 25% { clip-path: polygon(50% 20%, 80% 50%, 50% 80%, 20% 50%); } 50% { clip-path: polygon(50% 0%, 50% 0%, 50% 100%, 50% 100%); } 75% { clip-path: polygon(50% 20%, 80% 50%, 50% 80%, 20% 50%); } 100% { clip-path: polygon(50% 0%, 50% 0%, 50% 100%, 50% 100%); } }',
        '.pacman { animation: pacman-move 3s ease-in-out infinite; }',
        '.pacman-body { animation: pacman-mouth 0.6s ease-in-out infinite; }',
        '</style>',
        '</defs>',
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
            svg_lines.append(f'<rect x="{x}" y="{y}" width="{cell_size}" height="{cell_size}" fill="{color}" class="contribution" rx="1" ry="1" title="Contributions: {count}"/>')
    
    pacman_x = x_offset + cols * (cell_size + gap) + 40
    pacman_y = y_offset + (rows * (cell_size + gap)) / 2
    
    svg_lines.extend([
        f'<g class="pacman" transform="translate({pacman_x}, {pacman_y})">',
        f'<circle cx="0" cy="0" r="10" fill="#FFD700" class="pacman-body"/>',
        f'<circle cx="4" cy="-3" r="1.5" fill="{bg_color}"/>',
        '</g>',
    ])
    
    for i in range(3):
        pellet_x = pacman_x - 30 + (i * 15)
        pellet_y = pacman_y
        svg_lines.append(f'<circle cx="{pellet_x}" cy="{pellet_y}" r="2" fill="#FFD700" opacity="0.6"/>')
    
    svg_lines.append('</svg>')
    return '\n'.join(svg_lines)

def main():
    print(f"Generating Pac-Man contribution graph for {GITHUB_USERNAME}...")
    weeks = get_contributions_data()
    if not weeks:
        print("Failed to fetch data. Using sample data...")
        import random
        weeks = [[{'contributionCount': random.randint(0, 30), 'date': str(datetime.now() - timedelta(days=d))} for d in range(7)] for i in range(52)]
    
    grid = contributions_to_grid(weeks)
    svg_dark = create_pacman_svg(grid, dark_mode=True)
    svg_light = create_pacman_svg(grid, dark_mode=False)
    
    dark_path = OUTPUT_DIR / 'pacman-contribution-graph-dark.svg'
    light_path = OUTPUT_DIR / 'pacman-contribution-graph.svg'
    
    with open(dark_path, 'w') as f:
        f.write(svg_dark)
    print(f"✓ Dark mode graph: {dark_path}")
    
    with open(light_path, 'w') as f:
        f.write(svg_light)
    print(f"✓ Light mode graph: {light_path}")

if __name__ == '__main__':
    main()
