"""Activities: generate variations and inline assets."""

from __future__ import annotations

import json
import re
from pathlib import Path

from temporalio import activity

from adforge.activities.types import (
    PlayableBuildResult,
    VariationsInput,
    VariationsResult,
)
from adforge.utils import file_size_mb, file_to_data_url, slug

CONFIG_RE = re.compile(r"const\s+CONFIG\s*=\s*(\{.*?\})\s*;", re.S)


def _parse_js_config(block: str) -> dict:
    s = block
    s = re.sub(r"//[^\n]*", "", s)
    s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
    s = re.sub(r"'", '"', s)
    s = re.sub(r",\s*([}\]])", r"\1", s)
    s = re.sub(r"([{,]\s*)([A-Za-z_][A-Za-z0-9_]*)\s*:", r'\1"\2":', s)
    return json.loads(s)


@activity.defn(name="generate_variations")
async def generate_variations(inp: VariationsInput) -> VariationsResult:
    html = Path(inp.base_html_path).read_text(encoding="utf-8")
    m = CONFIG_RE.search(html)
    if not m:
        raise RuntimeError("No CONFIG block found in base playable.")
    base_cfg = _parse_js_config(m.group(1))

    out_dir = Path(inp.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    base_stem = Path(inp.base_html_path).stem

    paths: list[str] = []
    for v in inp.variants:
        cfg = {**base_cfg, **v.overrides}
        new_block = "const CONFIG = " + json.dumps(cfg, indent=2) + ";"
        new_html = html[: m.start()] + new_block + html[m.end():]
        target = out_dir / f"{base_stem}__{slug(v.name)}.html"
        target.write_text(new_html, encoding="utf-8")
        paths.append(str(target))
        activity.logger.info(f"variant {v.name} → {target} ({file_size_mb(target):.2f} MB)")
    return VariationsResult(files=paths)


# ───── asset inlining ──────────────────────────────────────────────────────────


EXTERNAL_RE = re.compile(r"^(https?:|//|data:)", re.I)
URL_RE = re.compile(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)")


def _inline_one(html: str, base: Path) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(src=True):
        if not EXTERNAL_RE.match(tag["src"]):
            target = (base / tag["src"]).resolve()
            if target.exists():
                tag["src"] = file_to_data_url(target)

    for link in soup.find_all("link", rel=lambda v: v and "stylesheet" in v):
        href = link.get("href")
        if not href or EXTERNAL_RE.match(href):
            continue
        target = (base / href).resolve()
        if target.exists():
            css = target.read_text(encoding="utf-8")
            css = URL_RE.sub(lambda mt: _rewrite_css(mt, target.parent), css)
            style = soup.new_tag("style")
            style.string = css
            link.replace_with(style)

    for script in soup.find_all("script", src=True):
        src = script["src"]
        if EXTERNAL_RE.match(src):
            continue
        target = (base / src).resolve()
        if target.exists():
            del script["src"]
            script.string = target.read_text(encoding="utf-8")

    for style in soup.find_all("style"):
        if style.string:
            style.string = URL_RE.sub(lambda mt: _rewrite_css(mt, base), style.string)
    return str(soup)


def _rewrite_css(m: re.Match[str], base: Path) -> str:
    ref = m.group(1).strip()
    if EXTERNAL_RE.match(ref):
        return m.group(0)
    target = (base / ref).resolve()
    if not target.exists():
        return m.group(0)
    return f"url('{file_to_data_url(target)}')"


_JS_SRC_RE = re.compile(r"""(\.src\s*=\s*['"])(\./[^'"]+)(['"])""")
_JS_AUDIO_RE = re.compile(r"""(new\s+Audio\s*\(\s*['"])(\./[^'"]+)(['"]\s*\))""")


def _inline_js_assets(html: str, asset_dir: Path) -> str:
    """Inline JS-level asset references: img.src = './file.png' and new Audio('./file.ogg')."""
    def _replace(m: re.Match[str]) -> str:
        prefix, rel_path, suffix = m.group(1), m.group(2), m.group(3)
        filename = rel_path.lstrip("./")
        target = asset_dir / filename
        if target.exists():
            return prefix + file_to_data_url(target) + suffix
        return m.group(0)
    html = _JS_SRC_RE.sub(_replace, html)
    html = _JS_AUDIO_RE.sub(_replace, html)
    return html


@activity.defn(name="inline_html_assets")
async def inline_html_assets(html_path: str) -> PlayableBuildResult:
    p = Path(html_path)
    html = p.read_text(encoding="utf-8")
    html = _inline_one(html, p.parent)
    asset_dirs = [p.parent]
    run_dir = p.parent
    manifest_path = run_dir / "manifest.json"
    if manifest_path.exists():
        try:
            manifest = json.loads(manifest_path.read_text())
            project_id = manifest.get("project_id")
            if project_id:
                from adforge.config import PROJECTS_DIR
                proj_assets = PROJECTS_DIR / project_id / "assets"
                if proj_assets.is_dir():
                    asset_dirs.insert(0, proj_assets)
        except Exception:
            pass
    for adir in asset_dirs:
        html = _inline_js_assets(html, adir)
    p.write_text(html, encoding="utf-8")
    return PlayableBuildResult(html_path=str(p), size_mb=file_size_mb(p))
