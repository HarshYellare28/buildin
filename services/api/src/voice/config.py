import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parents[4]
load_dotenv(REPO_ROOT / ".env")


def _flag(name: str, default: bool) -> bool:
    return os.getenv(name, "1" if default else "0").lower() in ("1", "true", "yes")


@dataclass(frozen=True)
class Settings:
    api_key: str
    api_base: str
    stt_model: str
    tts_model: str
    tts_speaker: str
    llm_model: str
    patient_lang: str
    caregiver_lang: str
    dawa_api_url: str
    # Speech timeouts are generous; the classifier's is short on purpose — a slow LLM
    # must never stall a live dose call, since classify.py falls back to regex.
    speech_timeout: float
    llm_timeout: float
    llm_classify_enabled: bool

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


def load_settings() -> Settings:
    return Settings(
        api_key=os.getenv("SARVAM_API_KEY", "").strip(),
        api_base=os.getenv("SARVAM_API_BASE", "https://api.sarvam.ai").rstrip("/"),
        stt_model=os.getenv("SARVAM_STT_MODEL", "saaras:v3"),
        tts_model=os.getenv("SARVAM_TTS_MODEL", "bulbul:v3"),
        tts_speaker=os.getenv("SARVAM_TTS_SPEAKER", "ritu"),
        llm_model=os.getenv("SARVAM_LLM_MODEL", "sarvam-105b"),
        patient_lang=os.getenv("DEMO_PATIENT_LANG", "hi-IN"),
        caregiver_lang=os.getenv("DEMO_CAREGIVER_LANG", "en-IN"),
        dawa_api_url=os.getenv("DAWA_API_URL", "http://localhost:8000").rstrip("/"),
        speech_timeout=float(os.getenv("VOICE_SPEECH_TIMEOUT", "20")),
        llm_timeout=float(os.getenv("VOICE_LLM_TIMEOUT", "8")),
        llm_classify_enabled=_flag("VOICE_LLM_CLASSIFY", True),
    )


settings = load_settings()
