"""Temporal worker — long-running process that hosts activities + workflows.

    uv run adforge worker
    uv run adforge run creative --project castle_clashers
    uv run adforge run playable --project castle_clashers
"""

from __future__ import annotations

import asyncio
import logging

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter
from temporalio.worker import Worker

from adforge import activities, pipelines
from adforge.config import ensure_dirs, settings


async def amain() -> None:
    s = settings()
    ensure_dirs()
    client = await Client.connect(
        s.temporal_address,
        namespace=s.temporal_namespace,
        data_converter=pydantic_data_converter,
    )
    worker = Worker(
        client,
        task_queue=s.temporal_task_queue,
        workflows=pipelines.WORKFLOWS,
        activities=activities.ALL,
    )
    logging.getLogger().setLevel(logging.INFO)
    print(f"[worker] connected → {s.temporal_address} / {s.temporal_namespace}")
    print(f"[worker] task queue → {s.temporal_task_queue}")
    print(f"[worker] workflows  → {[w.__name__ for w in pipelines.WORKFLOWS]}")
    print(f"[worker] activities → {len(activities.ALL)}")
    print("[worker] running. ctrl-c to stop.")
    await worker.run()


def main() -> None:
    asyncio.run(amain())


if __name__ == "__main__":
    main()
