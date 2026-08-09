"""Read-only access to repo fixtures. Never mutate these files."""

from __future__ import annotations

import json
from functools import lru_cache

from ..config import FIXTURES_DIR


@lru_cache(maxsize=1)
def load_people() -> dict:
    with (FIXTURES_DIR / "people.json").open(encoding="utf-8") as fh:
        return json.load(fh)


@lru_cache(maxsize=1)
def load_formulary() -> list[dict]:
    with (FIXTURES_DIR / "formulary.json").open(encoding="utf-8") as fh:
        return json.load(fh)["medications"]


def formulary_by_id() -> dict[str, dict]:
    return {m["id"]: m for m in load_formulary()}


def formulary_by_name() -> dict[str, dict]:
    return {m["name_normalized"]: m for m in load_formulary()}
