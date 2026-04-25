"""Activities: small disk-IO helpers used by workflows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from temporalio import activity


@activity.defn(name="write_json")
async def write_json(args: dict[str, Any]) -> str:
    path = Path(args["path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(args["data"], indent=2, ensure_ascii=False))
    return str(path)
