"""Activity: read a project's design docs (GDDs, READMEs, .txt) and produce a
clean game title + genre + summary in plain English.

Why: project.json's `category_id` is ugly App Store taxonomy that the user
shouldn't have to set. Instead we let the GAME ITSELF tell us what it is —
read the GDD, ask Claude to summarize, then later in the pipeline let
SensorTower's own search pick the matched app and we read its actual
category from SensorTower's response (no hardcoded mapping).

Result is cached at `.cache/project_intel/<project>__<hash>.json` keyed on
the doc content hash, so re-runs are free.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pydantic import BaseModel, Field
from temporalio import activity

from adforge.config import CACHE_DIR
from adforge.connectors import claude
from adforge.utils import extract_docx_text, strip_json_fences

CACHE_DIR_DOCS = CACHE_DIR / "project_intel"


class ProjectIntelInput(BaseModel):
    project_id: str
    project_dir: str


class ProjectIntel(BaseModel):
    project_id: str
    title: str                       # clean title pulled from the docs
    genre: str                       # plain-English, e.g. "bullet-heaven roguelike"
    summary: str                     # 2-3 sentence game description
    sources: list[str] = Field(default_factory=list)
    inferred_from_docs: bool = True


SYSTEM = (
    "You read mobile-game design documents and produce a one-shot summary "
    "for a downstream creative pipeline. You output ONLY JSON — no preamble, "
    "no fences, no commentary."
)

PROMPT_TPL = """The team is building an ad creative for this game. Read the design docs and produce a clean summary that the rest of the pipeline can use.

Project folder name: {project_name}

Design docs:
---
{docs}
---

Output JSON:
{{
  "title": "<the actual game title from the docs (not the folder name)>",
  "genre": "<plain-English genre, 2-5 words: e.g. 'bullet-heaven roguelike', 'word puzzle solitaire', 'one-touch physics destruction'>",
  "summary": "<2-3 sentence summary of the core loop, the input, the win/lose condition, and the audience>"
}}
"""


def _gather_doc_text(project_dir: Path) -> tuple[str, list[str]]:
    chunks: list[str] = []
    sources: list[str] = []
    for f in sorted(project_dir.iterdir()):
        if not f.is_file():
            continue
        suffix = f.suffix.lower()
        if suffix == ".docx":
            t = extract_docx_text(f)
            if t.strip():
                chunks.append(f"## {f.name}\n{t}")
                sources.append(f.name)
        elif suffix in (".md", ".txt"):
            try:
                t = f.read_text(encoding="utf-8", errors="ignore")[:30_000]
            except Exception:
                t = ""
            if t.strip():
                chunks.append(f"## {f.name}\n{t}")
                sources.append(f.name)
    return "\n\n".join(chunks), sources


def _cache_path(project_id: str, content_hash: str) -> Path:
    return CACHE_DIR_DOCS / f"{project_id}__{content_hash}.json"


@activity.defn(name="analyze_project_docs")
async def analyze_project_docs(inp: ProjectIntelInput) -> ProjectIntel:
    project_dir = Path(inp.project_dir)

    full_text, sources = _gather_doc_text(project_dir)
    if not full_text.strip():
        return ProjectIntel(
            project_id=inp.project_id,
            title=inp.project_id.replace("_", " ").title(),
            genre="unknown",
            summary="No design docs found in project folder.",
            sources=[],
            inferred_from_docs=False,
        )

    digest = hashlib.sha256(full_text.encode()).hexdigest()[:16]
    cache_file = _cache_path(inp.project_id, digest)
    if cache_file.is_file():
        try:
            cached = json.loads(cache_file.read_text())
            activity.logger.info(f"[project_intel] cache hit for {inp.project_id} ({digest})")
            return ProjectIntel(**cached)
        except Exception:
            pass

    activity.heartbeat(f"asking Claude for genre of {inp.project_id} from {len(sources)} doc(s)")
    prompt = PROMPT_TPL.format(
        project_name=inp.project_id,
        docs=full_text[:25_000],
    )
    raw = claude.complete(prompt, system=SYSTEM, model=claude.HAIKU, max_tokens=512, temperature=0.0)

    try:
        data = json.loads(strip_json_fences(raw))
    except Exception as e:
        activity.logger.warning(f"[project_intel] JSON parse failed: {e} — raw: {raw[:200]}")
        return ProjectIntel(
            project_id=inp.project_id,
            title=inp.project_id.replace("_", " ").title(),
            genre="unknown",
            summary="Claude response unparseable.",
            sources=sources,
            inferred_from_docs=False,
        )

    result = ProjectIntel(
        project_id=inp.project_id,
        title=str(data.get("title") or inp.project_id),
        genre=str(data.get("genre") or "unknown"),
        summary=str(data.get("summary") or ""),
        sources=sources,
        inferred_from_docs=True,
    )

    CACHE_DIR_DOCS.mkdir(parents=True, exist_ok=True)
    cache_file.write_text(result.model_dump_json(indent=2))
    activity.logger.info(
        f"[project_intel] {inp.project_id} → title='{result.title}' genre='{result.genre}'"
    )
    return result
