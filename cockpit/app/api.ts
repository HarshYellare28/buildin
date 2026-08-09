import { CarePacket, LedgerEvent, Medication, TranscriptLine } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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

export async function triggerDose(planId: string): Promise<{
  dose_id: string;
  status: "calling";
  medication: Medication;
}> {
  return request("/doses/trigger", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan_id: planId, simulate_time: "evening" }),
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
