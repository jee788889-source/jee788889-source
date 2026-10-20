"""Render assets/activity.svg from the real GitHub contribution calendar.

Usage: GITHUB_TOKEN=... python scripts/activity.py <username>
"""
import json
import os
import sys
import urllib.request
from datetime import date

QUERY = """query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{
  totalContributions weeks{contributionDays{date contributionCount}}}}}}"""
LEVELS = ["#2a0f1c", "#6b1638", "#a3195a", "#d6246f", "#ff4f9a"]


def fetch(user, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"u": user}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        body = json.load(r)
    if "errors" in body:
        sys.exit(f"GitHub API error: {body['errors']}")
    return body["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def level(n, peak):
    return 0 if n == 0 else min(4, 1 + (n - 1) * 4 // max(peak, 1))


def streaks(days):
    best = cur = 0
    for d in days:
        cur = cur + 1 if d["contributionCount"] else 0
        best = max(best, cur)
    return best


def render(cal):
    weeks = cal["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    peak = max((d["contributionCount"] for d in days), default=0)
    active = sum(1 for d in days if d["contributionCount"])
    cell, gap, x0, y0 = 16, 4, 48, 196
    cells, months, last_m = [], [], None
    for wi, w in enumerate(weeks):
        for d in w["contributionDays"]:
            dt = date.fromisoformat(d["date"])
            x, y = x0 + wi * (cell + gap), y0 + ((dt.weekday() + 1) % 7) * (cell + gap)
            lv = level(d["contributionCount"], peak)
            cls = ' class="hot"' if lv else ""
            cells.append(f'<rect{cls} x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{LEVELS[lv]}">'
                         f'<title>{d["date"]}: {d["contributionCount"]}</title></rect>')
            if dt.day <= 7 and dt.month != last_m and dt.weekday() == 6:
                months.append(f'<text x="{x}" y="{y0 - 12}">{dt.strftime("%b")}</text>')
                last_m = dt.month
    stats = [(cal["totalContributions"], "CONTRIBUTIONS"), (active, "ACTIVE DAYS"), (streaks(days), "LONGEST STREAK")]
    stat_svg = "".join(
        f'<text x="{1152 - i * 170}" y="96" text-anchor="end" class="serif" font-size="40" fill="#fdf2f8">{v:,}</text>'
        f'<text x="{1152 - i * 170}" y="120" text-anchor="end" class="mono" font-size="11" fill="#b48a9d" letter-spacing="2">{k}</text>'
        for i, (v, k) in enumerate(reversed(stats)))
    first, last = days[0]["date"], days[-1]["date"]
    legend = "".join(f'<rect x="{1040 + i * 22}" y="370" width="16" height="16" rx="3" fill="{c}"/>' for i, c in enumerate(LEVELS))
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 410" width="1200" height="410" role="img" aria-labelledby="t">
  <title id="t">A year of building: {cal['totalContributions']} contributions from {first} to {last}, {active} active days.</title>
  <defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#140810"/><stop offset="1" stop-color="#2a0b1b"/></linearGradient></defs>
  <style>
    .serif {{ font-family: Georgia, "Times New Roman", serif; }} .mono {{ font-family: ui-monospace, Consolas, monospace; }}
    .hot {{ animation: hot 2.4s ease-in-out infinite; }}
    @keyframes hot {{ 50% {{ opacity: .55; }} }}
    @media (prefers-reduced-motion: reduce) {{ .hot {{ animation: none; }} }}
  </style>
  <rect x=".5" y=".5" width="1199" height="409" rx="18" fill="url(#bg)" stroke="#5c1430"/>
  <text x="48" y="58" class="mono" font-size="13" fill="#e0267a" letter-spacing="3">04 · COMMIT LOG</text>
  <text x="48" y="108" class="serif" font-size="34" fill="#fdf2f8">A year of building, <tspan font-style="italic" fill="#f9a8d4">one square at a time.</tspan></text>
  {stat_svg}
  <g class="mono" font-size="11" fill="#b48a9d">{''.join(months)}</g>
  {''.join(cells)}
  <text x="48" y="384" class="mono" font-size="11" fill="#b48a9d" letter-spacing="1">{first} → {last} · REAL GITHUB DATA</text>
  <text x="1030" y="383" text-anchor="end" class="mono" font-size="11" fill="#b48a9d">LESS</text>{legend}<text x="1150" y="383" class="mono" font-size="11" fill="#b48a9d">MORE</text>
</svg>
"""


if __name__ == "__main__":
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token or len(sys.argv) != 2:
        sys.exit("usage: GITHUB_TOKEN=... python scripts/activity.py <username>")
    cal = fetch(sys.argv[1], token)
    assert cal["weeks"], "empty contribution calendar"
    out = os.path.join(os.path.dirname(__file__), "..", "assets", "activity.svg")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(render(cal))
    print(f"wrote {out}: {cal['totalContributions']} contributions")
