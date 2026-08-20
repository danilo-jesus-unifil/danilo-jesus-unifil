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
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from linguist_catalog import (
    FILE_TYPE_COLORS,
    KNOWN_EXTENSIONS,
    LANGUAGE_COLORS,
    SPECIAL_FILE_TYPES,
)

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
OUTPUTS = {
    "metrics": ASSETS / "github-profile-metrics.svg",
    "languages": ASSETS / "github-profile-languages.svg",
    "file_types": ASSETS / "github-profile-file-types.svg",
}
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
FONT_FAMILY = "'Atkinson Hyperlegible Next', 'Noto Sans', sans-serif"

TIMESTAMP_RE = re.compile(r"\d{2}/\d{2}/\d{4} \d{2}:\d{2}")

LANGUAGE_COLORS = {
    "JavaScript": "#f1e05a",
    "TypeScript": "#3178c6",
    "Python": "#3572A5",
    "HTML": "#e34c26",
    "CSS": "#663399",
    "Java": "#b07219",
    "C": "#555555",
    "C++": "#f34b7d",
    "C#": "#7355dd",
    "PHP": "#4F5D95",
    "Shell": "#89e051",
    "Dart": "#00B4AB",
    "Kotlin": "#A97BFF",
    "Go": "#00ADD8",
    "Rust": "#dea584",
    "Slint": "#2379F4",
    "PowerShell": "#012456",
    "Markdown": "#083fa1",
    "JSON": "#292929",
    "XML": "#0060ac",
    "SVG": "#ff9900",
    "SQL": "#e38c00",
    "Ruby": "#701516",
    "Swift": "#F05138",
    "Vue": "#41b883",
    "Svelte": "#ff3e00",
    "Astro": "#ff5a03",
    "Lua": "#000080",
    "R": "#198CE7",
    "Scala": "#c22d40",
    "Haskell": "#5e5086",
    "Elixir": "#6e4a7e",
    "Erlang": "#B83998",
    "Clojure": "#db5855",
    "TOML": "#9c4221",
    "YAML": "#cb171e",
    "Dockerfile": "#384d54",
    "Makefile": "#427819",
    "CMake": "#DA3434",
    "Nix": "#7e7eff",
    "Zig": "#ec915c",
    "Assembly": "#6E4C13",
    "Objective-C": "#438eff",
    "Objective-C++": "#6866fb",
    "Gradle": "#02303a",
    "GraphQL": "#e10098",
    "Jupyter Notebook": "#DA5B0B",
}
FALLBACK_COLORS = [GOLD_LIGHT, GOLD, "#b9a77f", "#c9a227", MUTED, BLUE]

SPECIAL_FILE_TYPES = {
    "dockerfile": "Dockerfile",
    "makefile": "Makefile",
    "cmakelists.txt": "CMakeLists.txt",
    "license": "LICENSE",
    ".gitignore": ".gitignore",
}

FILE_TYPE_COLORS = {
    "dockerfile": "#384d54",
    "makefile": "#427819",
    "cmakelists.txt": "#DA3434",
    "license": "#8fa6c4",
    ".js": "#f1e05a",
    ".mjs": "#f1e05a",
    ".cjs": "#f1e05a",
    ".ts": "#3178c6",
    ".tsx": "#3178c6",
    ".jsx": "#f1e05a",
    ".py": "#3572A5",
    ".ps1": "#012456",
    ".psd1": "#012456",
    ".psm1": "#012456",
    ".rs": "#dea584",
    ".slint": "#2379F4",
    ".sh": "#89e051",
    ".bash": "#89e051",
    ".zsh": "#89e051",
    ".fish": "#89e051",
    ".html": "#e34c26",
    ".htm": "#e34c26",
    ".css": "#663399",
    ".scss": "#c6538c",
    ".sass": "#a53b70",
    ".less": "#1d365d",
    ".java": "#b07219",
    ".c": "#555555",
    ".h": "#555555",
    ".cpp": "#f34b7d",
    ".cc": "#f34b7d",
    ".cxx": "#f34b7d",
    ".cs": "#7355dd",
    ".php": "#4F5D95",
    ".dart": "#00B4AB",
    ".kt": "#A97BFF",
    ".kts": "#A97BFF",
    ".go": "#00ADD8",
    ".md": "#083fa1",
    ".markdown": "#083fa1",
    ".json": "#292929",
    ".xml": "#0060ac",
    ".svg": "#ff9900",
    ".sql": "#e38c00",
    ".rb": "#701516",
    ".swift": "#F05138",
    ".vue": "#41b883",
    ".svelte": "#ff3e00",
    ".astro": "#ff5a03",
    ".lua": "#000080",
    ".r": "#198CE7",
    ".scala": "#c22d40",
    ".hs": "#5e5086",
    ".ex": "#6e4a7e",
    ".exs": "#6e4a7e",
    ".erl": "#B83998",
    ".hrl": "#B83998",
    ".clj": "#db5855",
    ".cljs": "#db5855",
    ".toml": "#9c4221",
    ".yml": "#cb171e",
    ".yaml": "#cb171e",
    ".nix": "#7e7eff",
    ".zig": "#ec915c",
    ".asm": "#6E4C13",
    ".s": "#6E4C13",
    ".m": "#438eff",
    ".mm": "#6866fb",
    ".gradle": "#02303a",
    ".graphql": "#e10098",
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
    for extension in KNOWN_EXTENSIONS:
        if lowered.endswith(extension):
            return extension
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
        '<defs><linearGradient id="eco-bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0e0c16"/><stop offset="1" stop-color="#0b0910"/></linearGradient></defs>',
        '<rect width="100%" height="100%" rx="14" fill="url(#eco-bg)"/>',
        f'<rect x="5" y="5" width="{width - 10}" height="{height - 10}" rx="11" fill="none" stroke="{GOLD}" stroke-opacity="0.35"/>',
        f'<text x="28" y="34" fill="{GOLD_LIGHT}" font-family="{FONT_FAMILY}" font-size="13" font-weight="700" letter-spacing="1.5">{esc("Perfil do Github")}</text>',
        f'<line x1="24" y1="52" x2="856" y2="52" stroke="{GOLD}" stroke-opacity="0.25"/>',
    ]


def card_frame(width: int, height: int, label: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" role="img" aria-label="{esc(label)}">',
        '<defs><linearGradient id="profile-bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#0e0c16"/><stop offset="1" stop-color="#0b0910"/></linearGradient></defs>',
        '<rect width="100%" height="100%" rx="14" fill="url(#profile-bg)"/>',
        f'<rect x="5" y="5" width="{width - 10}" height="{height - 10}" rx="11" fill="none" stroke="{GOLD}" stroke-opacity="0.35"/>',
    ]


def close_svg(lines: list[str]) -> str:
    lines.append('</svg>')
    return "\n".join(lines) + "\n"


def metric_card(x: int, y: int, width: int, label: str, value: object, color: str) -> str:
    value_text = compact(value, 14)
    value_size = 23 if len(value_text) <= 10 else 18
    return "".join(
        [
            f'<rect x="{x}" y="{y}" width="{width}" height="66" rx="8" fill="{SURFACE}" stroke="{GOLD}" stroke-opacity="0.22"/>',
            f'<text x="{x + 14}" y="{y + 30}" fill="{color}" font-family="{FONT_FAMILY}" font-size="{value_size}" font-weight="700">{esc(value_text)}</text>',
            f'<text x="{x + 14}" y="{y + 53}" fill="{MUTED}" font-family="{FONT_FAMILY}" font-size="10.5" letter-spacing="0.35">{esc(label)}</text>',
        ]
    )


def metrics_svg(data: dict) -> str:
    width, height = 520, 240
    lines = card_frame(width, height, "Perfil do Github")
    lines.extend(
        [
            f'<text x="28" y="35" fill="{GOLD_LIGHT}" font-family="{FONT_FAMILY}" font-size="15" font-weight="700" letter-spacing="1.2">Perfil do Github</text>',
            f'<line x1="24" y1="54" x2="{width - 24}" y2="54" stroke="{GOLD}" stroke-opacity="0.25"/>',
        ]
    )
    metric_values = [
        ("Linguagens", len(data["languages"]), GREEN),
        ("Repositórios analisados", data["analyzed_repositories"], PURPLE),
        ("Códigos no total", human_bytes(data["code_bytes"]), GOLD),
        ("Total de arquivos", data["total_files"], RED),
    ]
    positions = [(24, 70), (264, 70), (24, 145), (264, 145)]
    for (label, value, color), (x, y) in zip(metric_values, positions):
        lines.append(metric_card(x, y, 232, label, value, color))
    lines.append(f'<line x1="24" y1="232" x2="{width - 24}" y2="232" stroke="{GOLD}" stroke-opacity="0.25"/>')
    return close_svg(lines)


def ranking_row(lines: list[str], x: int, y: int, width: int, label: str, percent: float, detail: str, color: str) -> None:
    track_x = x + 145
    info_x = x + width - 122
    track_width = info_x - track_x - 12
    fill_width = max(2, int(track_width * max(0.0, min(100.0, percent)) / 100.0))
    lines.extend(
        [
            f'<text x="{x + 14}" y="{y + 11}" fill="{PARCHMENT}" font-family="{FONT_FAMILY}" font-size="11">{esc(compact(label, 22))}</text>',
            f'<rect x="{track_x}" y="{y + 2}" width="{track_width}" height="11" rx="5.5" fill="{SURFACE}"/>',
            f'<rect x="{track_x}" y="{y + 2}" width="{fill_width}" height="11" rx="5.5" fill="{color}"/>',
            f'<text x="{info_x}" y="{y + 11}" fill="{MUTED}" font-family="{FONT_FAMILY}" font-size="9">{esc(detail)}</text>',
        ]
    )


def ranking_svg(data: dict, kind: str, limit: int = 20) -> str:
    is_language = kind == "languages"
    title = "Linguagens mais usadas" if is_language else "Tipos de arquivo"
    items = list(data["languages"].items()) if is_language else list(data["file_types"].items())
    items = items[:limit]
    row_step = 18
    include_footer = not is_language
    height = 76 + row_step * max(1, len(items)) + (40 if include_footer else 22)
    width = 520
    lines = card_frame(width, height, title)
    lines.append(f'<rect x="7" y="7" width="{width - 14}" height="{height - 14}" rx="10" fill="{BG}" fill-opacity="0.52" stroke="{GOLD}" stroke-opacity="0.24"/>')
    lines.append(f'<text x="21" y="33" fill="{GOLD_LIGHT}" font-family="{FONT_FAMILY}" font-size="12" font-weight="700" letter-spacing="0.65">{esc(title)}</text>')
    lines.append(f'<line x1="19" y1="48" x2="{width - 21}" y2="48" stroke="{GOLD}" stroke-opacity="0.18"/>')

    total = (data["code_bytes"] if is_language else data["total_files"]) or 1
    for index, (item, value) in enumerate(items):
        numeric = int(value)
        percent = numeric / total * 100
        if is_language:
            detail = f"{percent:.1f}% · {human_bytes(numeric)}"
            color = LANGUAGE_COLORS.get(item, FALLBACK_COLORS[index % len(FALLBACK_COLORS)])
            label = item
        else:
            detail = f"{percent:.1f}% · {numeric} arq."
            color = FILE_TYPE_COLORS.get(item.casefold(), FALLBACK_COLORS[index % len(FALLBACK_COLORS)])
            label = pretty_file_type(item)
        ranking_row(lines, 7, 58 + index * row_step, width - 14, label, percent, detail, color)

    if include_footer:
        footer = f"Última atualização: {data['generated'].replace(' ', ' às ')}"
        lines.append(f'<text x="21" y="{height - 14}" fill="{DIM}" font-family="{FONT_FAMILY}" font-size="9">{esc(footer)}</text>')
    return close_svg(lines)


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
    changed = {
        "metrics": write_if_changed(OUTPUTS["metrics"], metrics_svg(data)),
        "languages": write_if_changed(OUTPUTS["languages"], ranking_svg(data, "languages", 20)),
        "file_types": write_if_changed(OUTPUTS["file_types"], ranking_svg(data, "file_types", 20)),
    }
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
