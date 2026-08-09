import { CockpitState } from "./types";

export const DISCHARGE_TEXT = `Discharge Advice / Discharged Summary
Pt: Smt. Lakshmi, 68Y F
Dx: HTN, T2DM (follow-up)

Medicines (continue at home):
1) Amlodipine 5 mg — roj raat ko 1 tablet
2) Metformin 500 mg — subah + raat, khane ke saath
3) Atorvastatin 10 mg — raat
4) Paracetamol 500 mg — bukhar ho to SOS

Notes: BP dawai skip mat karna. Agar pet kharab / jalan ho to doctor / family ko batao.`;

export function initialState(): CockpitState {
  return {
    activeTab: "ingest",
    ingestMode: "paste",
    pasteText: DISCHARGE_TEXT,
    busy: false,
    planId: null,
    planStatus: "draft",
    reviewed: false,
    meds: [],
    callMedicationId: null,
    doseId: null,
    doseStatus: "idle",
    outboundAttemptId: null,
    voiceSessionId: null,
    transcript: [],
    mealText: "",
    mealCheck: null,
    packet: null,
    events: [],
    photoDataUrl: null,
    photoFile: null,
    error: null,
  };
}
