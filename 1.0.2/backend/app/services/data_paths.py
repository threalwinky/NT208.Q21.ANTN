from __future__ import annotations

import os
from pathlib import Path


def resolve_data_dir() -> Path:
    env_value = os.getenv("DATA_DIR")
    if env_value:
        return Path(env_value).expanduser().resolve()

    current = Path(__file__).resolve()
    local_data_dir = current.parents[2] / "data"
    candidates = [
        Path("/app/data"),
        local_data_dir,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return local_data_dir.resolve()
