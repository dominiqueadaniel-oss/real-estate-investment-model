"""Loads playbook.yaml into plain Python dicts used throughout the model."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

DEFAULT_PLAYBOOK_PATH = Path(__file__).resolve().parent.parent / "playbook.yaml"


def load_playbook(path: str | Path | None = None) -> dict[str, Any]:
    playbook_path = Path(path) if path else DEFAULT_PLAYBOOK_PATH
    with open(playbook_path, "r") as f:
        return yaml.safe_load(f)
