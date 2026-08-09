import json

from .config import FIXTURES_DIR
from .models import Plan


def _load_json(name: str) -> dict:
    with open(FIXTURES_DIR / name, encoding="utf-8") as f:
        return json.load(f)


class Store:
    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        people = _load_json("people.json")
        self.people = people
        self.formulary = _load_json("formulary.json")["medications"]
        self.plans: dict[str, Plan] = {}
        self.events: list[dict] = []
        self._plan_seq = 0
        self._event_seq = 0

    def next_plan_id(self) -> str:
        self._plan_seq += 1
        return f"plan_demo_{self._plan_seq}"

    def next_event_id(self) -> str:
        self._event_seq += 1
        return f"evt_{self._event_seq}"


store = Store()
