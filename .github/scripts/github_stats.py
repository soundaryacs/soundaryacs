"""Renders assets/github-stats.svg from public GitHub data for both accounts.

Run by .github/workflows/stats.yml; needs GITHUB_TOKEN in the environment.
"""
import json
import os
import urllib.request
from collections import Counter
from pathlib import Path

USERS = ["soundaryacs", "soundaryacshcl"]
MARKUP = {"HTML", "CSS", "SCSS", "Smarty", "Jupyter Notebook"}
OUT = Path(__file__).resolve().parents[2] / "assets" / "github-stats.svg"

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    contributionsCollection {
      totalCommitContributions
      totalPullRequestContributions
      contributionCalendar { totalContributions }
    }
    repositories(first: 100, ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false) {
      totalCount
      nodes {
        stargazerCount
        forkCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name color } }
        }
      }
    }
  }
}
"""


def fetch(login):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {os.environ['GITHUB_TOKEN']}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        body = json.load(resp)
    if "errors" in body:
        raise SystemExit(body["errors"])
    return body["data"]["user"]


def collect():
    stats = Counter()
    sizes, colors = Counter(), {}
    for login in USERS:
        u = fetch(login)
        c = u["contributionsCollection"]
        repos = u["repositories"]
        stats["contributions"] += c["contributionCalendar"]["totalContributions"]
        stats["commits"] += c["totalCommitContributions"]
        stats["prs"] += c["totalPullRequestContributions"]
        stats["repos"] += repos["totalCount"]
        stats["followers"] += u["followers"]["totalCount"]
        for r in repos["nodes"]:
            stats["stars"] += r["stargazerCount"]
            stats["forks"] += r["forkCount"]
            for e in r["languages"]["edges"]:
                if e["node"]["name"] in MARKUP:
                    continue
                sizes[e["node"]["name"]] += e["size"]
                colors[e["node"]["name"]] = e["node"]["color"] or "#94a3b8"
    stats["bytes"] = sum(sizes.values())
    return stats, sizes, colors


def render(stats, sizes, colors):
    rows = [
        ("Contributions (past year)", f'{stats["contributions"]:,}'),
        ("Commits (past year)", f'{stats["commits"]:,}'),
        ("Public Repositories", f'{stats["repos"]:,}'),
        ("Community Forks", f'{stats["forks"]:,}'),
        ("Languages Used", f"{len(sizes)}"),
        ("Followers", f'{stats["followers"]:,}'),
        ("Code Written", f'{stats["bytes"] / 1e6:.1f} MB'),
        ("Accounts", f"{len(USERS)}"),
    ]
    total = stats["bytes"] or 1
    top = sizes.most_common(6)

    left = "".join(
        f'<text x="40" y="{118 + i * 38}" class="sans" font-size="16" fill="#cbd5e1">{k}</text>'
        f'<text x="540" y="{118 + i * 38}" class="sans" font-size="16" font-weight="700" fill="#fff" text-anchor="end">{v}</text>'
        for i, (k, v) in enumerate(rows)
    )
    bar, x = "", 640
    for name, size in top:
        w = 480 * size / total
        bar += f'<rect x="{x:.1f}" y="96" width="{w:.1f}" height="10" fill="{colors[name]}"/>'
        x += w
    langs = "".join(
        f'<circle cx="648" cy="{148 + i * 38}" r="6" fill="{colors[n]}"/>'
        f'<text x="664" y="{154 + i * 38}" class="sans" font-size="16" fill="#cbd5e1">{n}</text>'
        f'<rect x="830" y="{145 + i * 38}" width="220" height="8" rx="4" fill="#ffffff" fill-opacity="0.06"/>'
        f'<rect x="830" y="{145 + i * 38}" width="{220 * s / top[0][1]:.1f}" height="8" rx="4" fill="{colors[n]}"/>'
        f'<text x="1120" y="{154 + i * 38}" class="sans" font-size="16" font-weight="700" fill="#fff" text-anchor="end">{100 * s / total:.1f}%</text>'
        for i, (n, s) in enumerate(top)
    )
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1160" height="440" viewBox="0 0 1160 440">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0b1020"/><stop offset="1" stop-color="#231c4a"/></linearGradient>
    <style>.sans{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Helvetica,Arial,sans-serif}}</style>
  </defs>
  <rect x="1" y="1" width="578" height="438" rx="20" fill="url(#bg)" stroke="#ffffff" stroke-opacity="0.1"/>
  <text x="40" y="58" class="sans" font-size="22" font-weight="700" fill="#67e8f9">GitHub Statistics</text>
  <line x1="40" y1="78" x2="540" y2="78" stroke="#ffffff" stroke-opacity="0.12"/>
  {left}
  <rect x="600" y="1" width="558" height="438" rx="20" fill="url(#bg)" stroke="#ffffff" stroke-opacity="0.1"/>
  <text x="640" y="58" class="sans" font-size="22" font-weight="700" fill="#67e8f9">Most Used Languages</text>
  <line x1="640" y1="78" x2="1120" y2="78" stroke="#ffffff" stroke-opacity="0.12"/>
  {bar}
  {langs}
  <text x="640" y="412" class="sans" font-size="13" fill="#94a3b8">@{" + @".join(USERS)} · public repos · updated daily</text>
</svg>
'''


if __name__ == "__main__":
    OUT.write_text(render(*collect()))
    print("wrote", OUT)
