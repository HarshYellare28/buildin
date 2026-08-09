"""L0 check: prove the key works and both speech APIs are real.

    cd services/api/src && python -m voice.verify_sarvam

Synthesises a Hindi line, writes it to a wav, then sends that wav back through STT. A clean
round-trip means TTS and STT are both live. It also prints the script Saaras returns
(Devanagari vs Latin), which the classifier regexes depend on.
"""

import sys
from pathlib import Path

from .classify import classify
from .config import REPO_ROOT, settings
from .sarvam_client import SarvamError, synthesize, transcribe

LINE = "Namaste Lakshmi ji. Kya aapne Amlodipine 5mg le li?"
PATIENT_LINE = "Haan, le li. Lekin pet mein jalan ho rahi hai."
OUT = REPO_ROOT / "data" / "local" / "voice-verify"  # data/local/ is already gitignored


def main() -> int:
    if not settings.configured:
        print("FAIL: SARVAM_API_KEY not set. Copy .env.example to .env at the repo root.")
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    print(f"base={settings.api_base}  tts={settings.tts_model}/{settings.tts_speaker}  stt={settings.stt_model}")

    for name, text in (("agent", LINE), ("patient", PATIENT_LINE)):
        try:
            audio = synthesize(text)
        except SarvamError as exc:
            print(f"FAIL tts[{name}]: {exc}")
            return 1
        path = OUT / f"{name}.wav"
        path.write_bytes(audio)
        print(f"OK  tts[{name}]  {len(audio)} bytes -> {path}")

        try:
            heard = transcribe(audio, filename=f"{name}.wav", content_type="audio/wav")
        except SarvamError as exc:
            print(f"FAIL stt[{name}]: {exc}")
            return 1
        print(f"OK  stt[{name}]  lang={heard.language_code}  transcript={heard.text!r}")

        if name == "patient":
            result = classify(heard.text)
            print(
                f"    classify -> adherence={result.adherence} exception={result.exception_type} "
                f"symptom={result.normalized_symptom} conf={result.confidence:.2f} src={result.source}"
            )
            if result.notes:
                print(f"    notes: {result.notes}")

    print("\nPASS: key valid, Bulbul TTS and Saaras STT both live.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
