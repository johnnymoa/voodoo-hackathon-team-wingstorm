"""Feedback — per-run notes you (the human) leave for the /iterate skill.

Each run can have a single `feedback.md` at `runs/<run_id>/feedback.md`:

    ---
    status: open                       # open | fulfilled | wontfix
    created_at: 2026-04-25T13:42:00+00:00
    updated_at: 2026-04-25T13:42:00+00:00
    addressed_in_run: null             # filled in when an iteration ships
    addressed_by_config: null          # config_id that addressed this
    ---
    The brief is too generic. Push the labeler harder on opening hooks.
    Try Claude instead of Mistral for pattern extraction.

The /iterate skill (in .claude/skills/iterate/SKILL.md) reads open feedback,
proposes a new PipelineConfig that addresses it, runs the new config, and
closes the loop by setting `status: fulfilled` and linking the new run.

Frontmatter parsing is intentionally lite: a flat list of `key: value` pairs
with string/null scalar values, no quoting, no nesting. Keep it simple.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel

from adforge.config import RUNS_DIR

STATUS_OPEN = "open"
STATUS_FULFILLED = "fulfilled"
STATUS_WONTFIX = "wontfix"
ALLOWED_STATUSES = {STATUS_OPEN, STATUS_FULFILLED, STATUS_WONTFIX}

_META_KEYS = ("status", "created_at", "updated_at", "addressed_in_run", "addressed_by_config")


class Feedback(BaseModel):
    run_id: str
    status: str = STATUS_OPEN
    created_at: str
    updated_at: str
    addressed_in_run: str | None = None
    addressed_by_config: str | None = None
    body: str = ""


def _path(run_id: str) -> Path:
    return RUNS_DIR / run_id / "feedback.md"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split `---\\n key: value \\n---\\n body` into ({...}, "body").

    Returns ({}, text) if there's no frontmatter.
    Only flat scalars are supported; values are returned as strings (or None
    for `null`/empty).
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, text

    meta: dict[str, Any] = {}
    end = -1
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
        if ":" in lines[i]:
            k, _, v = lines[i].partition(":")
            k = k.strip()
            v = v.strip()
            meta[k] = None if (v == "" or v.lower() == "null") else v

    if end == -1:
        # malformed — no closing fence; treat as no frontmatter.
        return {}, text

    body = "\n".join(lines[end + 1 :]).lstrip("\n")
    return meta, body


def _render(fb: Feedback) -> str:
    lines = [
        "---",
        f"status: {fb.status}",
        f"created_at: {fb.created_at}",
        f"updated_at: {fb.updated_at}",
        f"addressed_in_run: {fb.addressed_in_run if fb.addressed_in_run else 'null'}",
        f"addressed_by_config: {fb.addressed_by_config if fb.addressed_by_config else 'null'}",
        "---",
        "",
        fb.body.strip(),
        "",
    ]
    return "\n".join(lines)


def load(run_id: str) -> Feedback | None:
    """Read feedback for one run, or None if no feedback file exists."""
    p = _path(run_id)
    if not p.is_file():
        return None
    text = p.read_text(encoding="utf-8")
    meta, body = _parse_frontmatter(text)
    return Feedback(
        run_id=run_id,
        status=str(meta.get("status") or STATUS_OPEN),
        created_at=str(meta.get("created_at") or _now_iso()),
        updated_at=str(meta.get("updated_at") or _now_iso()),
        addressed_in_run=meta.get("addressed_in_run"),
        addressed_by_config=meta.get("addressed_by_config"),
        body=body,
    )


def save(run_id: str, body: str, status: str | None = None) -> Feedback:
    """Create or update feedback for a run. Server fills timestamps."""
    if status is not None and status not in ALLOWED_STATUSES:
        raise ValueError(f"invalid status '{status}'. Allowed: {sorted(ALLOWED_STATUSES)}")

    existing = load(run_id)
    now = _now_iso()
    fb = Feedback(
        run_id=run_id,
        status=status or (existing.status if existing else STATUS_OPEN),
        created_at=existing.created_at if existing else now,
        updated_at=now,
        addressed_in_run=existing.addressed_in_run if existing else None,
        addressed_by_config=existing.addressed_by_config if existing else None,
        body=body,
    )

    p = _path(run_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(_render(fb), encoding="utf-8")
    return fb


def close(run_id: str, *, addressed_in_run: str, addressed_by_config: str) -> Feedback:
    """Mark feedback fulfilled and link the run/config that addressed it."""
    existing = load(run_id)
    if existing is None:
        raise FileNotFoundError(f"no feedback at {_path(run_id)}")

    existing.status = STATUS_FULFILLED
    existing.addressed_in_run = addressed_in_run
    existing.addressed_by_config = addressed_by_config
    existing.updated_at = _now_iso()

    _path(run_id).write_text(_render(existing), encoding="utf-8")
    return existing


def set_status(run_id: str, status: str) -> Feedback:
    """Change just the status — used by the wontfix path."""
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"invalid status '{status}'. Allowed: {sorted(ALLOWED_STATUSES)}")
    existing = load(run_id)
    if existing is None:
        raise FileNotFoundError(f"no feedback at {_path(run_id)}")
    existing.status = status
    existing.updated_at = _now_iso()
    _path(run_id).write_text(_render(existing), encoding="utf-8")
    return existing


def list_all(*, status: str | None = None) -> list[Feedback]:
    """Walk runs/ and return every feedback file. Optionally filter by status."""
    if not RUNS_DIR.exists():
        return []
    out: list[Feedback] = []
    for run_dir in sorted(RUNS_DIR.iterdir(), reverse=True):
        if not run_dir.is_dir() or run_dir.name.startswith("_"):
            continue
        fb = load(run_dir.name)
        if fb is None:
            continue
        if status and fb.status != status:
            continue
        out.append(fb)
    return out
