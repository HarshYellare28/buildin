import {
  CarePacket,
  LedgerEvent,
  MealCheck,
  Medication,
  OutboundCall,
  TranscriptLine,
} from "./types";

const API_URL =
  process.env.NEXT_PUBLIC_API_URL ||
  (process.env.NODE_ENV === "production" ? "/api" : "http://localhost:8000");

interface ApiErrorBody {
  error?: { message?: string };
  detail?: { error?: { message?: string } } | string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, init);
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = (await response.json()) as ApiErrorBody;
      message =
        body.error?.message ||
        (typeof body.detail === "object" ? body.detail?.error?.message : body.detail) ||
        message;
    } catch {
      // Keep the HTTP status when the response is not JSON.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

export async function resetWorld(): Promise<void> {
  await request("/demo/reset", { method: "POST" });
}

export async function getActivePlan(): Promise<{
  id: string;
  status: "active";
  medications: Medication[];
} | null> {
  return request("/plans/active");
}

export async function extractPlan(input: {
  source: "paste" | "ocr";
  text?: string;
  file?: File;
}): Promise<{ plan_id: string; status: "draft"; medications: Medication[] }> {
  if (input.source === "ocr") {
    const form = new FormData();
    form.set("source", "ocr");
    if (input.file) form.set("file", input.file);
    return request("/plans/extract", { method: "POST", body: form });
  }
  return request("/plans/extract", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source: "paste", text: input.text || "" }),
  });
}

export async function saveAndActivatePlan(planId: string, medications: Medication[]): Promise<void> {
  await request(`/plans/${planId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ medications }),
  });
  await request(`/plans/${planId}/activate`, { method: "POST" });
}

export async function triggerDose(planId: string, medicationId: string): Promise<{
  dose_id: string;
  status: "calling";
  medication: Medication;
}> {
  return request("/doses/trigger", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      plan_id: planId,
      medication_id: medicationId,
      simulate_time: "now",
    }),
  });
}

export async function startVoiceSession(doseId: string, medication: Medication): Promise<{
  session_id: string;
  assistant_text: string;
  turns: TranscriptLine[];
}> {
  return request("/voice/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      dose_id: doseId,
      medication,
      patient_name: "Lakshmi",
      caregiver_name: "Ananya",
      speak: false,
    }),
  });
}

export async function startOutboundDoseCall(doseId: string): Promise<{
  dose_id: string;
  status: "calling";
  attempt_id: string;
}> {
  return request(`/sarvam/outbound/${doseId}`, { method: "POST" });
}

export async function getOutboundDoseCall(doseId: string): Promise<OutboundCall> {
  return request(`/sarvam/outbound/${doseId}`);
}

export async function runDisasterFallback(sessionId: string): Promise<{
  state: string;
  complete_posted: boolean;
  complete_error: string | null;
  turns: TranscriptLine[];
}> {
  return request(`/voice/sessions/${sessionId}/turn-text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      user_text: "Haan, le li. Lekin pet mein jalan ho rahi hai.",
      speak: false,
    }),
  });
}

export async function getEvents(planId: string): Promise<LedgerEvent[]> {
  const result = await request<{ events: LedgerEvent[] }>(
    `/events?plan_id=${encodeURIComponent(planId)}`,
  );
  return result.events;
}

export async function getLatestPacket(planId: string): Promise<CarePacket> {
  return request(`/packets/latest?plan_id=${encodeURIComponent(planId)}`);
}

export async function scoreMeal(planId: string, mealText: string): Promise<MealCheck> {
  return request(`/plans/${encodeURIComponent(planId)}/meal-checks`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ meal_text: mealText, source: "caregiver" }),
  });
}

export async function getLatestMealCheck(planId: string): Promise<MealCheck | null> {
  return request(`/plans/${encodeURIComponent(planId)}/meal-checks/latest`);
}
