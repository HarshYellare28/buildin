export type Tab = "ingest" | "meds" | "dose" | "packet" | "ledger";
export type IngestMode = "paste" | "photo";
export type DoseStatus = "idle" | "calling" | "completed" | "failed";
export type PlanStatus = "draft" | "active";
export type Criticality = "low" | "med" | "high";
export type FoodRule = "with_food" | "none" | string;

export interface Medication {
  id: string;
  name_raw: string;
  name_normalized: string;
  dose: number;
  unit: string;
  route: string;
  schedule_text: string;
  times: string[];
  food_rule: FoodRule;
  duration_days: number;
  criticality: Criticality;
  confidence: number;
  source: string;
}

export interface TranscriptLine {
  role: "agent" | "patient" | "unknown";
  text: string;
}

export interface OutboundCall {
  dose_id: string;
  status: "calling" | "completed" | "failed";
  attempt_id: string | null;
  call_status: string | null;
  failure_reason: string | null;
  transcript: TranscriptLine[];
}

export type LedgerEventType =
  | "plan_created"
  | "plan_activated"
  | "dose_triggered"
  | "dose_started"
  | "dose_completed"
  | "exception_logged"
  | "packet_sent"
  | "policy_refused";

export interface LedgerEvent {
  id: string;
  ts: string;
  type: LedgerEventType;
  plan_id?: string | null;
  dose_id?: string | null;
  payload: Record<string, unknown>;
}

export interface CarePacket {
  id: string;
  patient_name: string;
  event_time: string;
  medication: string;
  status: string;
  exception: {
    type: string;
    patient_reported: string | null;
    normalized: string | null;
  };
  system_action: string;
  suggested_caregiver_actions: string[];
  confidence: number;
  needs_clinician: boolean;
  language: string;
}

export interface CockpitState {
  activeTab: Tab;
  ingestMode: IngestMode;
  pasteText: string;
  busy: boolean;
  planId: string | null;
  planStatus: PlanStatus;
  reviewed: boolean;
  meds: Medication[];
  callMedicationId: string | null;
  doseId: string | null;
  doseStatus: DoseStatus;
  outboundAttemptId: string | null;
  voiceSessionId: string | null;
  transcript: TranscriptLine[];
  packet: CarePacket | null;
  events: LedgerEvent[];
  photoDataUrl: string | null;
  photoFile: File | null;
  error: string | null;
}
