from typing import Literal, Optional

from pydantic import BaseModel


class Medication(BaseModel):
    id: str
    name_raw: str
    name_normalized: str
    dose: float
    unit: str
    route: str
    schedule_text: str
    times: list[str] = []
    food_rule: Literal["with_food", "none"]
    duration_days: Optional[int] = None
    criticality: Literal["low", "med", "high"]
    source: Literal["paste", "ocr"]
    confidence: float


class Plan(BaseModel):
    id: str
    status: Literal["draft", "active"]
    patient_id: str
    caregiver_id: str
    medications: list[Medication]


class ExtractRequest(BaseModel):
    text: str
    source: Literal["paste"] = "paste"


class ApiError(BaseModel):
    code: str
    message: str
