import { CockpitState, Medication } from "./types";

export const FORMULARY: Medication[] = [
  { id: "med_amlodipine", name_raw: "Amlodipine 5mg", dose: 5, unit: "mg", route: "oral", schedule_text: "Night", food_rule: "none", criticality: "high", confidence: 0.92 },
  { id: "med_metformin", name_raw: "Metformin 500mg", dose: 500, unit: "mg", route: "oral", schedule_text: "Morning + night", food_rule: "with_food", criticality: "med", confidence: 0.88 },
  { id: "med_atorvastatin", name_raw: "Atorvastatin 10mg", dose: 10, unit: "mg", route: "oral", schedule_text: "Night", food_rule: "none", criticality: "med", confidence: 0.9 },
  { id: "med_paracetamol", name_raw: "Paracetamol 500mg", dose: 500, unit: "mg", route: "oral", schedule_text: "SOS for fever", food_rule: "none", criticality: "low", confidence: 0.85 },
];

export const DISCHARGE_TEXT = `Discharge Advice / Discharged Summary
Pt: Smt. Lakshmi, 68Y F
Dx: HTN, T2DM (follow-up)

Medicines (continue at home):
1) Amlodipine 5 mg — roj raat ko 1 tablet
2) Metformin 500 mg — subah + raat, khane ke saath
3) Atorvastatin 10 mg — raat
4) Paracetamol 500 mg — bukhar ho to SOS

Notes: BP dawai skip mat karna. Agar pet kharab / jalan ho to doctor / family ko batao.`;

export const AGENT_LINE_1 =
  "Namaste Lakshmi ji. Raat ki BP dawai Amlodipine 5mg lene ka samay ho gaya hai. Kya aapne dawai le li?";
export const PATIENT_REPLY = "Haan, le li. Lekin pet mein jalan ho rahi hai.";
export const AGENT_LINE_2 =
  "Samajh gayi. Aapne Amlodipine le li, aur pet mein jalan batayi. Main yeh baat Ananya ko bhej rahi hoon. Kripya dohra mat lena.";

export function initialState(): CockpitState {
  return {
    role: "caregiver",
    activeTab: "ingest",
    ingestMode: "paste",
    pasteText: DISCHARGE_TEXT,
    extracting: false,
    planStatus: "draft",
    reviewed: false,
    meds: [],
    doseStatus: "idle",
    transcript: [],
    micBusy: false,
    packet: null,
    events: [],
    photoDataUrl: null,
    photoFile: null,
    extractError: null,
  };
}
