"""Gera cartões SVG para o perfil do GitHub do dono deste repositório.

O script usa a API oficial do GitHub, produz arquivos locais e não cria commits
por atividade de outros repositórios. A automação semanal só publica quando os
dados realmente mudam.
"""

from __future__ import annotations

import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
USER = os.environ.get("GH_USER", "danilo-jesus-unifil")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API_URL = "https://api.github.com"
GRAPHQL_URL = "https://api.github.com/graphql"

BG = "#0e0c16"
SURFACE = "#1d1729"
GOLD = "#d4a24e"
GOLD_LIGHT = "#e8c07a"
PARCHMENT = "#f4ecdd"
MUTED = "#a89a80"
DIM = "#77694f"
GREEN = "#3ddc84"
PURPLE = "#a68dad"
RED = "#e07a5f"

GRAPHQL_QUERY = """
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    login
    name
    contributionsCollection(from:$from, to:$to) {
      totalCommitContributions
      totalIssueContributions
      totalPullRequestContributions
      totalPullRequestReviewContributions
      restrictedContributionsCount
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
    repositories(first:1, privacy:PUBLIC, ownerAffiliations:OWNER) {
      totalCount
    }
  }
}
"""

TIMESTAMP_RE = re.compile(
    r"\d{4}-\d{2}-\d{2} \d{2}:\d{2} UTC"
)

LANGUAGE_COLORS = {
    "JavaScript": "#e8c07a",
    "TypeScript": "#d4a24e",
    "Python": "#c9a227",
    "HTML": "#e07a5f",
    "CSS": "#a68dad",
    "Java": "#c48f6b",
    "C": "#8fa6c4",
    "C++": "#7f9ec4",
    "C#": "#9a8fc4",
    "PHP": "#9b8fc4",
    "Shell": "#8fc49a",
    "Dart": "#8fbcc4",
    "Kotlin": "#b98fc4",
    "Go": "#8fc4c4",
    "Rust": "#c4926b",
}
FALLBACK_COLORS = [GOLD_LIGHT, GOLD, "#b9a77f", "#c9a227", MUTED, "#8fa6c4"]


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def headers() -> dict[str, str]:
    result = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "danilo-jesus-unifil-profile-panel",
    }
    if TOKEN:
        result["Authorization"] = f"Bearer {TOKEN}"
    return result


def json_request(url: str, *, payload: bytes | None = None) -> object:
    request = urllib.request.Request(
        url,
        data=payload,
        headers={**headers(), "Content-Type": "application/json"} if payload else headers(),
        method="POST" if payload else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        try:
            details = exc.read().decode("utf-8", errors="replace")[:240]
        except Exception:
            details = ""
        raise RuntimeError(f"GitHub HTTP {exc.code}: {details}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"falha de conexão com o GitHub: {exc.reason}") from exc


def api_get(path: str, params: dict[str, str] | None = None) -> object:
    url = API_URL + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    return json_request(url)


def graphql(query: str, variables: dict[str, str]) -> dict:
    if not TOKEN:
        raise RuntimeError(
            "GITHUB_TOKEN não encontrado. No GitHub Actions ele é fornecido "
            "automaticamente; para testar localmente use GITHUB_TOKEN=$(gh auth token)."
        )
    payload = json.dumps({"query": query, "variables": variables}).encode("utf-8")
    result = json_request(GRAPHQL_URL, payload=payload)
    if not isinstance(result, dict):
        raise RuntimeError("resposta inválida da API GraphQL")
    errors = result.get("errors") or []
    if errors:
        messages = "; ".join(str(error.get("message", "erro GraphQL")) for error in errors)
        raise RuntimeError(messages)
    return result


def collect_profile() -> dict:
    now = datetime.now(timezone.utc)
    variables = {
        "login": USER,
        "from": (now - timedelta(days=365)).strftime("%Y-%m-%dT00:00:00Z"),
        "to": now.strftime("%Y-%m-%dT23:59:59Z"),
    }
    result = graphql(GRAPHQL_QUERY, variables)
    user = ((result.get("data") or {}).get("user"))
    if not user:
        raise RuntimeError(f"usuário do GitHub não encontrado: {USER}")

    collection = user["contributionsCollection"]
    calendar = collection["contributionCalendar"]
    days = [
        day
        for week in calendar.get("weeks", [])
        for day in week.get("contributionDays", [])
    ]
    return {
        "login": user["login"],
        "name": user.get("name") or user["login"],
        "contributions": calendar["totalContributions"],
        "commits": collection["totalCommitContributions"],
        "issues": collection["totalIssueContributions"],
        "pull_requests": collection["totalPullRequestContributions"],
        "reviews": collection["totalPullRequestReviewContributions"],
        "restricted": collection["restrictedContributionsCount"],
        "repositories": user["repositories"]["totalCount"],
        "days": days,
        "generated": now.strftime("%Y-%m-%d %H:%M UTC"),
    }


def list_public_repositories() -> list[dict]:
    repositories: list[dict] = []
    for page in range(1, 6):
        batch = api_get(
            f"/users/{urllib.parse.quote(USER)}/repos",
            {"type": "owner", "sort": "updated", "per_page": "100", "page": str(page)},
        )
        if not isinstance(batch, list):
            break
        repositories.extend(repo for repo in batch if not repo.get("fork"))
        if len(batch) < 100:
            break
    return repositories


def collect_languages() -> dict[str, int]:
    totals: dict[str, int] = {}
    for repo in list_public_repositories():
        owner = repo.get("owner", {}).get("login", USER)
        name = repo.get("name")
        if not name:
            continue
        try:
            values = api_get(
                f"/repos/{urllib.parse.quote(str(owner))}/{urllib.parse.quote(str(name))}/languages"
            )
        except RuntimeError as exc:
            print(f"aviso: não foi possível ler as linguagens de {name}: {exc}")
            continue
        if not isinstance(values, dict):
            continue
        for language, size in values.items():
            totals[language] = totals.get(language, 0) + int(size)
    return dict(sorted(totals.items(), key=lambda pair: pair[1], reverse=True))


def human_bytes(value: int) -> str:
    if value >= 1024**3:
        return f"{value / 1024**3:.2f} GB"
    if value >= 1024**2:
        return f"{value / 1024**2:.2f} MB"
    if value >= 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value} B"


def frame(width: int, height: int, title: str, subtitle: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="{esc(title)}">',
        '<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0e0c16"/><stop offset="1" stop-color="#0b0910"/></linearGradient><linearGradient id="scan" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#d4a24e" stop-opacity="0"/><stop offset="0.5" stop-color="#e8c07a" stop-opacity="0.9"/><stop offset="1" stop-color="#d4a24e" stop-opacity="0"/></linearGradient></defs>',
        '<rect width="100%" height="100%" rx="14" fill="url(#bg)"/>',
        f'<rect x="5" y="5" width="{width - 10}" height="{height - 10}" rx="11" fill="none" stroke="{GOLD}" stroke-opacity="0.35"/>',
        f'<text x="28" y="35" fill="{GOLD_LIGHT}" font-family="DejaVu Sans Mono,monospace" font-size="14" font-weight="700" letter-spacing="2">◆ {esc(title)}</text>',
        f'<text x="28" y="54" fill="{DIM}" font-family="DejaVu Sans Mono,monospace" font-size="10" letter-spacing="1.2">{esc(subtitle)}</text>',
        f'<line x1="24" y1="66" x2="{width - 24}" y2="66" stroke="{GOLD}" stroke-opacity="0.25"/>',
        '<rect x="24" y="67" width="180" height="2" fill="url(#scan)" opacity="0.85"/>',
    ]


def metric(x: int, y: int, width: int, label: str, value: object, color: str = GOLD_LIGHT) -> str:
    return "".join(
        [
            f'<rect x="{x}" y="{y}" width="{width}" height="76" rx="8" fill="{SURFACE}" stroke="{GOLD}" stroke-opacity="0.22"/>',
            f'<text x="{x + 16}" y="{y + 31}" fill="{color}" font-family="DejaVu Sans Mono,monospace" font-size="25" font-weight="700">{esc(value)}</text>',
            f'<text x="{x + 16}" y="{y + 55}" fill="{MUTED}" font-family="DejaVu Sans Mono,monospace" font-size="10" letter-spacing="1">{esc(label)}</text>',
        ]
    )


def summary_svg(data: dict) -> str:
    lines = frame(880, 260, "RELATÓRIO DE CAMPO // GITHUB SNAPSHOT", "métricas oficiais via GitHub GraphQL · janela móvel de 365 dias")
    values = [
        (24, "CONTRIBUIÇÕES", data["contributions"], GOLD_LIGHT),
        (238, "COMMITS", data["commits"], GOLD),
        (452, "PULL REQUESTS", data["pull_requests"], GREEN),
        (666, "ISSUES", data["issues"], PURPLE),
        (24, "REVIEWS", data["reviews"], GOLD_LIGHT),
        (238, "REPOSITÓRIOS PÚBLICOS", data["repositories"], GOLD),
        (452, "RESTRITOS", data["restricted"], MUTED),
        (666, "STATUS", "ONLINE", GREEN),
    ]
    for index, (x, label, value, color) in enumerate(values):
        y = 86 if index < 4 else 174
        lines.append(metric(x, y, 198 if x != 666 else 190, label, value, color))
    lines.append(f'<text x="24" y="246" fill="{DIM}" font-family="DejaVu Sans Mono,monospace" font-size="9">atualizado automaticamente · {esc(data["generated"])}</text>')
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def language_color(language: str, index: int) -> str:
    return LANGUAGE_COLORS.get(language, FALLBACK_COLORS[index % len(FALLBACK_COLORS)])


def languages_svg(languages: dict[str, int], data: dict) -> str:
    top = list(languages.items())[:8]
    total = sum(languages.values()) or 1
    height = 132 + max(1, len(top)) * 27 + 34
    lines = frame(880, height, "LANGUAGE MATRIX // TOP LANGUAGES", "fonte local · repositórios públicos do perfil")
    lines.append(f'<text x="38" y="101" fill="{GOLD}" font-family="DejaVu Sans Mono,monospace" font-size="13" font-weight="700">{len(languages)} linguagens</text>')
    lines.append(f'<text x="215" y="101" fill="{MUTED}" font-family="DejaVu Sans Mono,monospace" font-size="11">· {human_bytes(total)} de código · {data["repositories"]} repositórios públicos</text>')
    y = 132
    for index, (language, size) in enumerate(top):
        percent = size / total * 100
        width = max(3, int(500 * size / total))
        color = language_color(language, index)
        lines.extend(
            [
                f'<text x="38" y="{y + 13}" fill="{PARCHMENT}" font-family="DejaVu Sans Mono,monospace" font-size="12">{esc(language)}</text>',
                f'<rect x="250" y="{y + 3}" width="500" height="12" rx="6" fill="{SURFACE}"/>',
                f'<rect x="250" y="{y + 3}" width="{width}" height="12" rx="6" fill="{color}"/>',
                f'<text x="764" y="{y + 13}" fill="{MUTED}" font-family="DejaVu Sans Mono,monospace" font-size="11">{percent:.1f}% · {human_bytes(size)}</text>',
            ]
        )
        y += 27
    lines.append(f'<text x="38" y="{height - 14}" fill="{DIM}" font-family="DejaVu Sans Mono,monospace" font-size="10">atualizado automaticamente · {esc(data["generated"])}</text>')
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def activity_svg(data: dict) -> str:
    width, height = 880, 300
    lines = frame(width, height, "ACTIVITY FIELD // ÚLTIMAS CONTRIBUIÇÕES", "contagem oficial de contribuições · últimos 30 dias")
    days = data.get("days", [])[-30:]
    counts = [int(day.get("contributionCount", 0)) for day in days]
    if not counts:
        counts = [0]
    max_count = max(counts) or 1
    chart_x, chart_y, chart_w, chart_h = 52, 96, 770, 150
    lines.append(f'<line x1="{chart_x}" y1="{chart_y + chart_h}" x2="{chart_x + chart_w}" y2="{chart_y + chart_h}" stroke="{DIM}" stroke-opacity="0.65"/>')
    lines.append(f'<line x1="{chart_x}" y1="{chart_y}" x2="{chart_x}" y2="{chart_y + chart_h}" stroke="{DIM}" stroke-opacity="0.65"/>')
    points: list[str] = []
    for index, count in enumerate(counts):
        x = chart_x + (chart_w * index / max(1, len(counts) - 1))
        y = chart_y + chart_h - (chart_h * count / max_count)
        points.append(f"{x:.1f},{y:.1f}")
        lines.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{GREEN}"/>')
    lines.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{GOLD_LIGHT}" stroke-width="2.5" stroke-linejoin="round"/>')
    lines.append(f'<text x="{chart_x}" y="{chart_y - 12}" fill="{MUTED}" font-family="DejaVu Sans Mono,monospace" font-size="10">0</text>')
    lines.append(f'<text x="{chart_x}" y="{chart_y - 25}" fill="{GOLD}" font-family="DejaVu Sans Mono,monospace" font-size="10">máximo: {max(counts)}</text>')
    if days:
        lines.append(f'<text x="{chart_x}" y="{chart_y + chart_h + 22}" fill="{DIM}" font-family="DejaVu Sans Mono,monospace" font-size="9">{esc(days[0].get("date", ""))}</text>')
        lines.append(f'<text x="{chart_x + chart_w - 78}" y="{chart_y + chart_h + 22}" fill="{DIM}" font-family="DejaVu Sans Mono,monospace" font-size="9">{esc(days[-1].get("date", ""))}</text>')
    lines.append(f'<text x="52" y="280" fill="{DIM}" font-family="DejaVu Sans Mono,monospace" font-size="9">total no período de 365 dias: {data["contributions"]} · atualizado automaticamente · {esc(data["generated"])}</text>')
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def stable_text(text: str) -> str:
    return TIMESTAMP_RE.sub("@TIMESTAMP@", text)


def write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and stable_text(path.read_text(encoding="utf-8")) == stable_text(content):
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    profile = collect_profile()
    languages = collect_languages()
    ASSETS.mkdir(parents=True, exist_ok=True)
    outputs = {
        "github-summary.svg": summary_svg(profile),
        "github-languages.svg": languages_svg(languages, profile),
        "github-activity.svg": activity_svg(profile),
    }
    changed = [name for name, content in outputs.items() if write_if_changed(ASSETS / name, content)]
    print(json.dumps({"user": USER, "changed": changed, "languages": len(languages)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
