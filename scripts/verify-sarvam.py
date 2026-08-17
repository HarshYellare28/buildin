#!/usr/bin/env python3
"""Prove the Sarvam key reaches all three endpoints the API actually uses.

    python3 scripts/verify-sarvam.py

Hits the network on purpose — this is the check the pytest suite deliberately
does not do. Run it when extraction or the dose call "does nothing": it
separates a dead key from a code path that was never entered.

Exit 0 = every surface live. Exit 1 = at least one failed, with the reason.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "services" / "api"))

from src.config import (  # noqa: E402
    DEMO_PATIENT_LANG,
    EXTRACT_MODE,
    SARVAM_MODEL,
    SARVAM_STT_MODEL,
    SARVAM_TTS_MODEL,
)
from src.services import extract, sarvam  # noqa: E402

PASS, FAIL = "\033[32mPASS\033[0m", "\033[31mFAIL\033[0m"


def check(label: str, fn) -> bool:
    started = time.monotonic()
    try:
        detail = fn()
    except Exception as exc:
        print(f"  {FAIL}  {label}\n        {exc}")
        return False
    print(f"  {PASS}  {label}  ({time.monotonic() - started:.1f}s)  {detail}")
    return True


def main() -> int:
    print(f"\nbase={sarvam.SARVAM_API_BASE}  extract_mode={EXTRACT_MODE}")
    if not sarvam.is_configured():
        print(f"\n  {FAIL}  SARVAM_API_KEY is empty — set it in .env\n")
        return 1

    audio: dict[str, bytes] = {}

    def chat() -> str:
        out = sarvam.chat([{"role": "user", "content": 'Reply with JSON only: {"ok":true}'}])
        return f"{SARVAM_MODEL} -> {out.strip()[:40]!r}"

    def tts() -> str:
        audio["wav"] = sarvam.text_to_speech(
            "Namaste, kya aapne dawai le li hai?", language_code=DEMO_PATIENT_LANG
        )
        return f"{SARVAM_TTS_MODEL} -> {len(audio['wav'])} bytes wav"

    def stt() -> str:
        if not audio.get("wav"):
            raise RuntimeError("skipped: TTS produced no audio to transcribe")
        text = sarvam.speech_to_text(audio["wav"], language_code=DEMO_PATIENT_LANG)
        return f"{SARVAM_STT_MODEL} -> {text[:48]!r}"

    def extract_note() -> str:
        note = (REPO_ROOT / "fixtures" / "discharge-messy.txt").read_text(encoding="utf-8")
        hits = extract._extract_via_sarvam(note)
        if not hits:
            raise RuntimeError("returned no medications from the demo fixture")
        return ", ".join(h["name_normalized"] for h in hits)

    print("\nsarvam surfaces")
    ok = [
        check("chat  /v1/chat/completions", chat),
        check("tts   /text-to-speech     ", tts),
        check("stt   /speech-to-text     ", stt),
    ]
    print("\nextract path")
    ok.append(check("POST /plans/extract LLM path", extract_note))

    if EXTRACT_MODE == "auto":
        print(
            "\n  note: EXTRACT_MODE=auto — the formulary parse matches the demo\n"
            "        fixture outright, so a real run never reaches Sarvam."
        )

    print()
    return 0 if all(ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
