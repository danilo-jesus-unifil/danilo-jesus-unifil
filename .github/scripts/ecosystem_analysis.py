"""Gera o cartão SVG de análise do ecossistema público do perfil.

A coleta usa somente a API oficial do GitHub, ignora forks e repositórios
privados e continua quando um repositório individual não pode ser analisado.
O workflow publica o SVG apenas quando os dados ou sua estrutura realmente
mudam; o horário de geração é ignorado nessa comparação.
"""

from __future__ import annotations

import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
OUTPUT = ASSETS / "github-ecosystem.svg"
USER = os.environ.get("GH_USER", "danilo-jesus-unifil")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
API_URL = "https://api.github.com"

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
BLUE = "#8fa6c4"

TIMESTAMP_RE = re.compile(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}")

LANGUAGE_COLORS = {
    "JavaScript": GOLD_LIGHT,
    "TypeScript": GOLD,
    "Python": "#c9a227",
    "HTML": RED,
    "CSS": PURPLE,
    "Java": "#c48f6b",
    "C": BLUE,
    "C++": "#7f9ec4",
    "C#": "#9a8fc4",
    "PHP": "#9b8fc4",
    "Shell": "#8fc49a",
    "Dart": "#8fbcc4",
    "Kotlin": "#b98fc4",
    "Go": "#8fc4c4",
    "Rust": "#c4926b",
}
FALLBACK_COLORS = [GOLD_LIGHT, GOLD, "#b9a77f", "#c9a227", MUTED, BLUE]

SPECIAL_FILE_TYPES = {
    "dockerfile": "Dockerfile",
    "makefile": "Makefile",
    "license": "LICENSE",
    ".gitignore": ".gitignore",
}

def esc(value: object) -> str:
    """Escapa qualquer valor antes de inseri-lo no SVG."""

    return html.escape(str(value), quote=True)


def compact(value: object, limit: int) -> str:
    text = str(value)
    return text if len(text) <= limit else text[: max(1, limit - 1)] + "…"


def headers() -> dict[str, str]:
    result = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "danilo-jesus-unifil-github-ecosystem-panel",
    }
    if TOKEN:
        result["Authorization"] = f"Bearer {TOKEN}"
    return result


def json_request(url: str) -> object:
    request = urllib.request.Request(url, headers=headers(), method="GET")
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


def list_public_repositories() -> list[dict]:
    """Lista todos os repositórios públicos próprios, ignorando forks."""

    repositories: list[dict] = []
    page = 1
    while True:
        batch = api_get(
            f"/users/{urllib.parse.quote(USER, safe='')}/repos",
            {
                "type": "owner",
                "sort": "updated",
                "direction": "desc",
                "per_page": "100",
                "page": str(page),
            },
        )
        if not isinstance(batch, list):
            raise RuntimeError("resposta inválida ao listar os repositórios públicos")
        for repo in batch:
            if not isinstance(repo, dict):
                continue
            owner = str((repo.get("owner") or {}).get("login") or USER)
            if repo.get("fork") or repo.get("private") or repo.get("visibility") == "private":
                continue
            if owner.casefold() != USER.casefold():
                continue
            repositories.append(repo)
        if len(batch) < 100:
            break
        page += 1
    return repositories


def collect_languages(repo: dict, warnings: list[str]) -> Counter[str]:
    owner = str((repo.get("owner") or {}).get("login") or USER)
    name = str(repo.get("name") or "")
    totals: Counter[str] = Counter()
    if not name:
        return totals
    try:
        values = api_get(
            f"/repos/{urllib.parse.quote(owner, safe='')}/{urllib.parse.quote(name, safe='')}/languages"
        )
    except RuntimeError as exc:
        warnings.append(f"linguagens indisponíveis: {name} ({compact(exc, 100)})")
        return totals
    if not isinstance(values, dict):
        warnings.append(f"linguagens indisponíveis: {name} (resposta inválida)")
        return totals
    for language, size in values.items():
        try:
            totals[str(language)] += int(size)
        except (TypeError, ValueError):
            warnings.append(f"tamanho de linguagem inválido: {name}")
    return totals


def collect_tree(repo: dict) -> tuple[list[dict], bool]:
    owner = str((repo.get("owner") or {}).get("login") or USER)
    name = str(repo.get("name") or "")
    branch = str(repo.get("default_branch") or "main")
    if not name:
        raise RuntimeError("repositório sem nome")
    tree = api_get(
        f"/repos/{urllib.parse.quote(owner, safe='')}/{urllib.parse.quote(name, safe='')}/git/trees/{urllib.parse.quote(branch, safe='')}",
        {"recursive": "1"},
    )
    if not isinstance(tree, dict) or not isinstance(tree.get("tree"), list):
        raise RuntimeError("resposta inválida da árvore Git")
    return tree["tree"], bool(tree.get("truncated"))


def file_type_for(path: str) -> str:
    basename = path.rsplit("/", 1)[-1]
    lowered = basename.casefold()
    if lowered in SPECIAL_FILE_TYPES:
        return SPECIAL_FILE_TYPES[lowered]
    suffix = Path(basename).suffix.casefold()
    if suffix:
        return suffix
    return "[sem extensão]"


def pretty_file_type(file_type: str) -> str:
    if file_type == "LICENSE":
        return "License"
    return file_type


def human_bytes(value: int) -> str:
    if value >= 1024**3:
        return f"{value / 1024**3:.2f} GB"
    if value >= 1024**2:
        return f"{value / 1024**2:.2f} MB"
    if value >= 1024:
        return f"{value / 1024:.1f} KB"
    return f"{value} B"


def collect_ecosystem() -> dict:
    repositories = list_public_repositories()
    languages: Counter[str] = Counter()
    file_types: Counter[str] = Counter()
    warnings: list[str] = []
    truncated: list[str] = []
    failed: list[str] = []
    total_files = 0

    for repo in repositories:
        name = str(repo.get("name") or "[sem nome]")
        languages.update(collect_languages(repo, warnings))
        try:
            entries, is_truncated = collect_tree(repo)
        except RuntimeError as exc:
            failed.append(name)
            warnings.append(f"árvore não analisada: {name} ({compact(exc, 100)})")
            continue
        if is_truncated:
            truncated.append(name)
            warnings.append(f"árvore truncada pelo GitHub: {name}")
        for entry in entries:
            if not isinstance(entry, dict) or entry.get("type") != "blob":
                continue
            path = str(entry.get("path") or "")
            if not path:
                continue
            try:
                size = int(entry.get("size") or 0)
            except (TypeError, ValueError):
                size = 0
            total_files += 1
            file_type = file_type_for(path)
            file_types[file_type] += 1

    generated = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M")
    return {
        "public_repositories": len(repositories),
        "analyzed_repositories": len(repositories) - len(failed),
        "languages": dict(languages.most_common()),
        "file_types": dict(file_types.most_common()),
        "total_files": total_files,
        "code_bytes": sum(languages.values()),
        "truncated": truncated,
        "failed": failed,
        "warnings": warnings,
        "generated": generated,
    }


def frame(width: int, height: int) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="{esc("GitHub de " + USER)}">',
        '<defs><linearGradient id="eco-bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0e0c16"/><stop offset="1" stop-color="#0b0910"/></linearGradient><linearGradient id="eco-scan" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#d4a24e" stop-opacity="0"/><stop offset="0.5" stop-color="#e8c07a" stop-opacity="0.9"/><stop offset="1" stop-color="#d4a24e" stop-opacity="0"/></linearGradient></defs>',
        '<rect width="100%" height="100%" rx="14" fill="url(#eco-bg)"/>',
        f'<rect x="5" y="5" width="{width - 10}" height="{height - 10}" rx="11" fill="none" stroke="{GOLD}" stroke-opacity="0.35"/>',
        f'<text x="28" y="34" fill="{GOLD_LIGHT}" font-family="monospace" font-size="13" font-weight="700" letter-spacing="1.5">◆ {esc("Atividade do Github")}</text>',
        f'<line x1="24" y1="52" x2="856" y2="52" stroke="{GOLD}" stroke-opacity="0.25"/>',
        '<rect x="24" y="53" width="205" height="2" fill="url(#eco-scan)" opacity="0.85"/>',
    ]


def metric_card(x: int, y: int, width: int, label: str, value: object, color: str) -> str:
    value_text = compact(value, 14)
    value_size = 20 if len(value_text) <= 10 else 16
    return "".join(
        [
            f'<rect x="{x}" y="{y}" width="{width}" height="66" rx="8" fill="{SURFACE}" stroke="{GOLD}" stroke-opacity="0.22"/>',
            f'<text x="{x + 13}" y="{y + 29}" fill="{color}" font-family="monospace" font-size="{value_size}" font-weight="700">{esc(value_text)}</text>',
            f'<text x="{x + 13}" y="{y + 51}" fill="{MUTED}" font-family="monospace" font-size="8.5" letter-spacing="0.5">{esc(label)}</text>',
        ]
    )


def panel(lines: list[str], x: int, y: int, width: int, height: int, title: str) -> None:
    lines.extend(
        [
            f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="10" fill="{BG}" fill-opacity="0.52" stroke="{GOLD}" stroke-opacity="0.24"/>',
            f'<text x="{x + 14}" y="{y + 22}" fill="{GOLD_LIGHT}" font-family="monospace" font-size="10" font-weight="700" letter-spacing="0.7">{esc(title)}</text>',
            f'<line x1="{x + 12}" y1="{y + 34}" x2="{x + width - 12}" y2="{y + 34}" stroke="{GOLD}" stroke-opacity="0.18"/>',
        ]
    )


def bar_row(lines: list[str], x: int, y: int, width: int, label: str, percent: float, detail: str, color: str, label_width: int) -> None:
    info_width = 112
    track_x = x + label_width
    info_x = x + width - info_width
    track_width = max(24, info_x - track_x - 12)
    fill_width = max(2, int(track_width * max(0.0, min(100.0, percent)) / 100.0))
    lines.extend(
        [
            f'<text x="{x + 14}" y="{y + 11}" fill="{PARCHMENT}" font-family="monospace" font-size="9.5">{esc(compact(label, 18))}</text>',
            f'<rect x="{track_x}" y="{y + 3}" width="{track_width}" height="9" rx="4.5" fill="{SURFACE}"/>',
            f'<rect x="{track_x}" y="{y + 3}" width="{fill_width}" height="9" rx="4.5" fill="{color}"/>',
            f'<text x="{info_x}" y="{y + 11}" fill="{MUTED}" font-family="monospace" font-size="8">{esc(detail)}</text>',
        ]
    )


def ecosystem_svg(data: dict) -> str:
    width, height = 880, 435
    lines = frame(width, height)
    metric_values = [
        ("Linguagens", len(data["languages"]), GREEN),
        ("Tipos de arquivo", len(data["file_types"]), GOLD_LIGHT),
        ("Repositórios analisados", data["analyzed_repositories"], PURPLE),
        ("Códigos no total", human_bytes(data["code_bytes"]), GOLD),
        ("Total de arquivos", data["total_files"], RED),
    ]
    metric_width = 160
    for index, (label, value, color) in enumerate(metric_values):
        lines.append(metric_card(24 + index * 168, 68, metric_width, label, value, color))

    left_x, right_x, panel_y, panel_w, panel_h = 24, 452, 147, 404, 250
    panel(lines, left_x, panel_y, panel_w, panel_h, "Linguagens mais usadas")
    panel(lines, right_x, panel_y, panel_w, panel_h, "Tipos de arquivo")

    languages = list(data["languages"].items())[:8]
    language_total = data["code_bytes"] or 1
    if languages:
        for index, (language, size) in enumerate(languages):
            percent = size / language_total * 100
            bar_row(
                lines,
                left_x,
                panel_y + 46 + index * 23,
                panel_w,
                language,
                percent,
                f"{percent:.1f}% · {human_bytes(size)}",
                LANGUAGE_COLORS.get(language, FALLBACK_COLORS[index % len(FALLBACK_COLORS)]),
                122,
            )
    else:
        lines.append(f'<text x="{left_x + 14}" y="{panel_y + 65}" fill="{MUTED}" font-family="monospace" font-size="9">Nenhuma linguagem retornada</text>')

    file_types = list(data["file_types"].items())[:10]
    file_total = data["total_files"] or 1
    if file_types:
        for index, (file_type, count) in enumerate(file_types):
            percent = count / file_total * 100
            bar_row(
                lines,
                right_x,
                panel_y + 46 + index * 19,
                panel_w,
                pretty_file_type(file_type),
                percent,
                f"{percent:.1f}% · {count} arq.",
                [GOLD_LIGHT, GOLD, GREEN, PURPLE, RED, BLUE][index % 6],
                78,
            )
    else:
        lines.append(f'<text x="{right_x + 14}" y="{panel_y + 65}" fill="{MUTED}" font-family="monospace" font-size="9">Nenhum arquivo retornado</text>')

    footer = f"Última atualização: {data['generated'].replace(' ', ' às ')}"
    lines.append(f'<text x="24" y="420" fill="{DIM}" font-family="monospace" font-size="8.5">{esc(footer)}</text>')
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
    data = collect_ecosystem()
    changed = write_if_changed(OUTPUT, ecosystem_svg(data))
    print(
        json.dumps(
            {
                "user": USER,
                "changed": changed,
                "public_repositories": data["public_repositories"],
                "analyzed_repositories": data["analyzed_repositories"],
                "languages": len(data["languages"]),
                "file_types": len(data["file_types"]),
                "files": data["total_files"],
                "truncated": data["truncated"],
                "failed": data["failed"],
                "warnings": len(data["warnings"]),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
