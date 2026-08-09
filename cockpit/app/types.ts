export type Role = "caregiver" | "patient";
export type Tab = "ingest" | "meds" | "dose" | "packet" | "ledger";
export type IngestMode = "paste" | "photo";
export type DoseStatus = "idle" | "calling" | "completed";
export type PlanStatus = "draft" | "active";
export type Criticality = "low" | "med" | "high";
export type FoodRule = "with_food" | "none";
export type Speaker = "agent" | "patient";
export type PatientLanguage = "Hindi" | "Kannada";

export interface Medication {
  id: string;
  name_raw: string;
  dose: number;
  unit: string;
  route: string;
  schedule_text: string;
  food_rule: FoodRule;
  criticality: Criticality;
  confidence: number;
  source?: "paste" | "ocr";
}

export interface TranscriptLine {
  speaker: Speaker;
  text: string;
}

export type LedgerEventType =
  | "plan_created"
  | "plan_activated"
  | "dose_triggered"
  | "dose_completed"
  | "exception_logged"
  | "packet_sent";

export interface LedgerEvent {
  id: string;
  ts: Date;
  type: LedgerEventType;
  description: string;
}

export interface CarePacket {
  patient_name: string;
  medication: string;
  status: string;
  exception: {
    type: string;
    patient_reported: string;
    normalized: string;
  };
  system_action: string;
  suggested_caregiver_actions: string[];
  confidence: number;
  needs_clinician: boolean;
  language: string;
}

export interface CockpitState {
  role: Role;
  activeTab: Tab;
  ingestMode: IngestMode;
  pasteText: string;
  extracting: boolean;
  planStatus: PlanStatus;
  reviewed: boolean;
  meds: Medication[];
  doseStatus: DoseStatus;
  transcript: TranscriptLine[];
  micBusy: boolean;
  packet: CarePacket | null;
  events: LedgerEvent[];
  photoDataUrl: string | null;
  photoFile: File | null;
  extractError: string | null;
}
