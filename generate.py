"""
Builds dark_mode.svg and light_mode.svg for the GitHub profile README.
Run locally with:  ACCESS_TOKEN=ghp_xxx python generate.py
Preview without a token:  python generate.py --offline
"""
import datetime
import os
import sys
from pathlib import Path
from xml.sax.saxutils import escape

import requests

# ---------------------------------------------------------------- settings
USER = "VincentDelisi"
BIRTHDAY = datetime.date(1999, 9, 3)
WIDTH = 60            # characters in the info panel
FONT_SIZE = 16
CHAR_W = FONT_SIZE * 0.6   # monospace glyph width
LINE_H = 20
PAD = 20
TOKEN = os.environ.get("ACCESS_TOKEN") or os.environ.get("GITHUB_TOKEN")

THEMES = {
    "dark":  dict(bg="#161b22", text="#c9d1d9", key="#ffa657", val="#a5d6ff", dots="#616e7f", art="#c9d1d9"),
    "light": dict(bg="#f6f8fa", text="#24292f", key="#953800", val="#0a3069", dots="#c2cfde", art="#24292f"),
}

FALLBACK_ART = r"""
                                    |
                                |  ###
                            |  ### ###
                           ### ###  |
                       |   ### ###
                      ###   |   |
                  |   ###
              |  ### ===
         |   ### ###  |
        ###  ###  |
    |   ###   |
   ###  ===
   ###   |
    |
 _______________________________________
  PJM . MISO . SERC       RT | DA | OPT
""".strip("\n")


# ---------------------------------------------------------------- GitHub data
def gql(query, variables):
    r = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": variables},
        headers={"Authorization": f"bearer {TOKEN}"},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    if "errors" in data:
        raise RuntimeError(data["errors"])
    return data["data"]


def github_stats():
    repo_q = """
    query($login: String!, $cursor: String) {
      user(login: $login) {
        createdAt
        followers { totalCount }
        repositories(first: 100, after: $cursor, ownerAffiliations: OWNER, isFork: false) {
          totalCount
          pageInfo { hasNextPage endCursor }
          nodes { stargazerCount }
        }
      }
    }"""
    stars, cursor = 0, None
    while True:
        user = gql(repo_q, {"login": USER, "cursor": cursor})["user"]
        repos = user["repositories"]
        stars += sum(n["stargazerCount"] for n in repos["nodes"])
        if not repos["pageInfo"]["hasNextPage"]:
            break
        cursor = repos["pageInfo"]["endCursor"]

    # commits: sum contribution years since account creation (API allows <= 1 year per query)
    commit_q = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) { totalCommitContributions }
      }
    }"""
    start = datetime.datetime.fromisoformat(user["createdAt"].replace("Z", "+00:00"))
    now = datetime.datetime.now(datetime.timezone.utc)
    commits = 0
    while start < now:
        end = min(start + datetime.timedelta(days=365), now)
        cc = gql(commit_q, {"login": USER, "from": start.isoformat(), "to": end.isoformat()})
        commits += cc["user"]["contributionsCollection"]["totalCommitContributions"]
        start = end

    return {
        "repos": repos["totalCount"],
        "stars": stars,
        "followers": user["followers"]["totalCount"],
        "commits": commits,
    }


def uptime():
    t, b = datetime.date.today(), BIRTHDAY
    y, m, d = t.year - b.year, t.month - b.month, t.day - b.day
    if d < 0:
        m -= 1
        d += (t.replace(day=1) - datetime.timedelta(days=1)).day
    if m < 0:
        y -= 1
        m += 12
    pl = lambda n, w: f"{n} {w}" + ("" if n == 1 else "s")
    return f"{pl(y, 'year')}, {pl(m, 'month')}, {pl(d, 'day')}"


# ---------------------------------------------------------------- line builders
# each line is a list of (style, text) segments; total text length == WIDTH
def kv(key, val, width=WIDTH, prefix=". "):
    dots = width - len(prefix) - len(key) - 1 - len(val) - 2
    return [("text", prefix), ("key", key), ("text", ":"),
            ("dots", " " + "." * max(dots, 1) + " "), ("val", val)]


def kv2(k1, v1, k2, v2):
    left = (WIDTH - 3) // 2
    return kv(k1, v1, left) + [("text", " | ")] + kv(k2, v2, WIDTH - 3 - left, prefix="")


def section(title):
    head = f"- {title} "
    return [("text", head + "-" * (WIDTH - len(head)))]


def header(user, host):
    head = f"{user}@{host} "
    return [("val", user), ("text", "@"), ("val", host),
            ("text", " " + "-" * (WIDTH - len(head)))]


BLANK = [("text", "")]


def info_lines(s):
    return [
        # ---- edit anything in this block ----
        header("vince", "delisi"),
        kv("OS", "Windows, Linux"),
        kv("Uptime", uptime()),
        kv("Host", "Quant Developer | Ex-RT Power Trader"),
        kv("Kernel", "PJM Certified Generation Dispatcher"),
        kv("IDE", "VS Code, Jupyter"),
        BLANK,
        kv("Languages.Programming", "Python, SQL"),
        kv("Languages.Real", "English"),
        BLANK,
        kv("Markets.Power", "PJM, MISO, SERC"),
        kv("Markets.Derivatives", "Options, Futures"),
        kv("Builds", "Dispatch, Storage Arb, Backtests"),
        BLANK,
        section("Contact"),
        kv("LinkedIn", "vincent-delisi"),
        kv("X", "@ivincentdelisi"),
        kv("GitHub", USER),
        BLANK,
        section("GitHub Stats"),
        kv2("Repos", f"{s['repos']:,}", "Stars", f"{s['stars']:,}"),
        kv2("Commits", f"{s['commits']:,}", "Followers", f"{s['followers']:,}"),
    ]


# ---------------------------------------------------------------- SVG
def render(theme, art, lines):
    c = THEMES[theme]
    art_w = max(len(l) for l in art) if art else 0
    info_x = PAD + art_w * CHAR_W + 30
    width = int(info_x + WIDTH * CHAR_W + PAD)
    rows = max(len(art), len(lines))
    height = int(PAD * 2 + rows * LINE_H)
    art_top = PAD + LINE_H + (rows - len(art)) * LINE_H / 2   # center art vertically
    info_top = PAD + LINE_H

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" font-family="Consolas, \'Courier New\', monospace" font-size="{FONT_SIZE}px">',
        "<style>"
        f".text{{fill:{c['text']}}} .key{{fill:{c['key']}}} .val{{fill:{c['val']}}} "
        f".dots{{fill:{c['dots']}}} .art{{fill:{c['art']}}} text{{white-space:pre}}"
        "</style>",
        f'<rect width="100%" height="100%" rx="15" fill="{c["bg"]}"/>',
    ]
    for i, line in enumerate(art):
        out.append(f'<text x="{PAD}" y="{art_top + i * LINE_H:.0f}" class="art" '
                   f'xml:space="preserve">{escape(line)}</text>')
    for i, segs in enumerate(lines):
        spans = "".join(f'<tspan class="{cls}">{escape(t)}</tspan>' for cls, t in segs)
        out.append(f'<text x="{info_x:.0f}" y="{info_top + i * LINE_H}" xml:space="preserve">{spans}</text>')
    out.append("</svg>")
    return "\n".join(out)


def main():
    if "--offline" in sys.argv or not TOKEN:
        if not TOKEN and "--offline" not in sys.argv:
            print("No ACCESS_TOKEN set; using placeholder stats.")
        stats = {"repos": 14, "stars": 1, "followers": 1, "commits": 198}
    else:
        stats = github_stats()

    art_file = Path("ascii.txt")
    art = (art_file.read_text(encoding="utf-8") if art_file.exists() else FALLBACK_ART).rstrip().split("\n")
    lines = info_lines(stats)
    for theme in THEMES:
        Path(f"{theme}_mode.svg").write_text(render(theme, art, lines), encoding="utf-8")
    print("Wrote dark_mode.svg and light_mode.svg", stats)


if __name__ == "__main__":
    main()
