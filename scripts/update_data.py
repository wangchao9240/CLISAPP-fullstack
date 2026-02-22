#!/usr/bin/env python3
import asyncio
import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "CLISApp-backend"
VENV_PYTHON = BACKEND_DIR / "venv" / "bin" / "python"

if VENV_PYTHON.exists() and Path(sys.executable).resolve() != VENV_PYTHON.resolve():
    os.execv(str(VENV_PYTHON), [str(VENV_PYTHON), str(Path(__file__).resolve())])

sys.path.insert(0, str(BACKEND_DIR))

from data_pipeline.config.grid_config import GRID_POINTS
from data_pipeline.downloads.openmeteo.fetch_realtime import OpenMeteoFetcher


async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    async with OpenMeteoFetcher() as fetcher:
        data = await fetcher.fetch_all_data(GRID_POINTS)

    output_path = BACKEND_DIR / "data" / "downloads" / "openmeteo" / "latest_fetch.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Saved {len(data)} points to {output_path}")
    print(f"Fetch timestamp (UTC): {datetime.now(timezone.utc).isoformat()}")


if __name__ == "__main__":
    asyncio.run(main())
