"use client";

import { useRef, useState } from "react";
import {
  AGENT_LINE_1,
  AGENT_LINE_2,
  FORMULARY,
  PATIENT_REPLY,
  initialState,
} from "./demoData";
import {
  ArrowRightIcon,
  CaregiverIcon,
  DoseTabIcon,
  IngestTabIcon,
  LedgerTabIcon,
  MedsTabIcon,
  MicIcon,
  PacketTabIcon,
  PasteIcon,
  PatientIcon,
  PhotoIcon,
  ResetIcon,
} from "./icons";
import {
  CarePacket,
  CockpitState,
  Criticality,
  FoodRule,
  IngestMode,
  LedgerEventType,
  Medication,
  PatientLanguage,
  Tab,
} from "./types";

const DEV_MODE = true;
const PATIENT_LANGUAGE: PatientLanguage = "Hindi";
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ApiMedication {
  id: string;
  name_raw: string;
  dose: number;
  unit: string;
  route: string;
  schedule_text: string;
  food_rule: FoodRule;
  criticality: Criticality;
  confidence: number;
  source: "paste" | "ocr";
}

function toMedication(m: ApiMedication): Medication {
  return {
    id: m.id,
    name_raw: m.name_raw,
    dose: m.dose,
    unit: m.unit,
    route: m.route,
    schedule_text: m.schedule_text,
    food_rule: m.food_rule,
    criticality: m.criticality,
    confidence: m.confidence,
    source: m.source,
  };
}

// Sarvam Doc AI only accepts PDF/JPEG/PNG.
const SARVAM_SUPPORTED_TYPES = new Set(["image/jpeg", "image/png", "application/pdf"]);
const SARVAM_SUPPORTED_LABEL = "JPEG, PNG, or PDF";

async function extractViaApi(opts: { source: "paste" | "ocr"; text?: string; file?: File }): Promise<Medication[]> {
  const form = new FormData();
  form.set("source", opts.source);
  if (opts.text) form.set("text", opts.text);
  if (opts.file) form.set("file", opts.file);

  const res = await fetch(`${API_URL}/plans/extract`, { method: "POST", body: form });
  if (!res.ok) {
    let message = `Extract failed (${res.status})`;
    try {
      const body = await res.json();
      message = body?.detail?.error?.message || message;
    } catch {
      // ignore parse failure, use default message
    }
    throw new Error(message);
  }
  const body = await res.json();
  return (body.medications as ApiMedication[]).map(toMedication);
}

const TYPE_LABELS: Record<LedgerEventType, string> = {
  plan_created: "Plan created",
  plan_activated: "Plan activated",
  dose_triggered: "Dose triggered",
  dose_completed: "Dose completed",
  exception_logged: "Exception logged",
  packet_sent: "Packet sent",
};

const confClass = (c: number) => (c < 0.8 ? "error" : c < 0.87 ? "warn" : "ok");
const cardStyleFor = (c: number): React.CSSProperties => {
  const k = confClass(c);
  if (k === "error") return { borderColor: "#b3491f" };
  if (k === "warn") return { borderColor: "var(--color-accent-600)" };
  return {};
};
const critTagClass = (c: Criticality) =>
  c === "high" ? "tag-accent" : c === "med" ? "tag-outline" : "tag-neutral";
const foodLabel = (f: FoodRule) => (f === "with_food" ? "with food" : "no food rule");
const speakerLabel = (sp: "agent" | "patient") =>
  sp === "agent" ? "DAWA (agent)" : "Lakshmi (patient)";

const tabBase: React.CSSProperties = {
  flex: 1,
  display: "flex",
  flexDirection: "column",
  alignItems: "center",
  gap: 3,
  padding: "9px 0 10px",
  background: "transparent",
  border: "none",
  cursor: "pointer",
};
const tabStyle = (active: boolean): React.CSSProperties => ({
  ...tabBase,
  color: active ? "var(--color-accent-700)" : "var(--color-neutral-700)",
  opacity: active ? 1 : 0.62,
});

function makeEvent(type: LedgerEventType, description: string) {
  return {
    id: "evt_" + Math.random().toString(36).slice(2, 8),
    ts: new Date(),
    type,
    description,
  };
}

export default function CockpitApp() {
  const [state, setState] = useState<CockpitState>(initialState);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const pushEvent = (type: LedgerEventType, description: string) => {
    setState((s) => ({ ...s, events: [...s.events, makeEvent(type, description)] }));
  };

  const selectRole = (role: "caregiver" | "patient") => setState((s) => ({ ...s, role }));
  const goToTab = (activeTab: Tab) => setState((s) => ({ ...s, activeTab }));

  const extract = async () => {
    const mode = state.ingestMode;
    const source: "paste" | "ocr" = mode === "photo" ? "ocr" : "paste";

    if (mode === "photo" && !state.photoFile) {
      setState((s) => ({ ...s, extractError: "Upload a photo first." }));
      return;
    }

    setState((s) => ({ ...s, extracting: true, extractError: null }));
    try {
      const meds = await extractViaApi({
        source,
        text: mode === "paste" ? state.pasteText : undefined,
        file: mode === "photo" ? state.photoFile! : undefined,
      });
      setState((s) => ({ ...s, extracting: false, meds }));
      pushEvent(
        "plan_created",
        mode === "photo"
          ? "Draft plan created from uploaded prescription photo (Sarvam Doc AI OCR)"
          : "Draft plan created from pasted discharge text"
      );
    } catch (err) {
      // API unreachable or the extract call failed — fall back to the local
      // demo formulary so the cockpit still demos, but surface the error.
      const message = err instanceof Error ? err.message : "Extract failed";
      setState((s) => ({
        ...s,
        extracting: false,
        extractError: `${message} — showing local demo data instead.`,
        meds: FORMULARY.map((m) => ({ ...m, source })),
      }));
      pushEvent("plan_created", `Draft plan created from local fallback data (API error: ${message})`);
    }
  };

  const onDoseChange = (id: string, val: number) => {
    setState((s) => ({
      ...s,
      meds: s.meds.map((m) => (m.id === id ? { ...m, dose: val } : m)),
    }));
  };

  const confirmActivate = () => {
    if (!state.reviewed || state.meds.length === 0) return;
    setState((s) => ({ ...s, planStatus: "active" }));
    pushEvent("plan_activated", "Plan confirmed and activated by caregiver");
  };

  const jumpEvening = () => {
    if (state.planStatus !== "active") return;
    setState((s) => ({
      ...s,
      doseStatus: "calling",
      transcript: [{ speaker: "agent", text: AGENT_LINE_1 }],
    }));
    pushEvent("dose_triggered", "Evening dose session triggered (demo clock)");
  };

  const completeDose = () => {
    setState((s) => ({ ...s, doseStatus: "completed", micBusy: false }));
    const packet: CarePacket = {
      patient_name: "Lakshmi",
      medication: "Amlodipine 5mg",
      status: "taken",
      exception: {
        type: "side_effect",
        patient_reported: "pet mein jalan",
        normalized: "abdominal_burning",
      },
      system_action: "Logged and escalated to caregiver. No new medication was invented or stopped.",
      suggested_caregiver_actions: [
        "Ask if burning is severe or with vomiting",
        "If severe, contact clinic on-call",
        "Do not double next dose",
      ],
      confidence: 0.86,
      needs_clinician: false,
      language: "en-IN",
    };
    setState((s) => ({
      ...s,
      packet,
      activeTab: s.role === "caregiver" ? "packet" : s.activeTab,
    }));
    pushEvent("dose_completed", "Dose marked taken via patient voice session");
    pushEvent("exception_logged", "Side effect reported — abdominal burning");
    pushEvent("packet_sent", "Caregiver packet generated and sent to Ananya");
  };

  const patientTapMic = () => {
    if (state.doseStatus !== "calling" || state.micBusy) return;
    setState((s) => ({ ...s, micBusy: true }));
    setState((s) => ({
      ...s,
      transcript: [...s.transcript, { speaker: "patient", text: PATIENT_REPLY }],
    }));
    setTimeout(() => {
      setState((s) => ({
        ...s,
        transcript: [...s.transcript, { speaker: "agent", text: AGENT_LINE_2 }],
      }));
      completeDose();
    }, 900);
  };

  const simulateComplete = () => {
    if (state.doseStatus !== "calling") return;
    setState((s) => ({
      ...s,
      transcript: [
        ...s.transcript,
        { speaker: "patient", text: PATIENT_REPLY },
        { speaker: "agent", text: AGENT_LINE_2 },
      ],
    }));
    completeDose();
  };

  const resetDemo = () => setState(initialState());

  const onPhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!SARVAM_SUPPORTED_TYPES.has(file.type)) {
      setState((s) => ({
        ...s,
        extractError: `"${file.name}" is a ${file.type || "unknown"} file — only ${SARVAM_SUPPORTED_LABEL} are supported. Please pick a different file.`,
      }));
      e.target.value = "";
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setState((s) => ({ ...s, photoDataUrl: String(reader.result), photoFile: file, extractError: null }));
    };
    reader.readAsDataURL(file);
  };

  const isCaregiver = state.role === "caregiver";
  const extractSourceLabel =
    state.meds.length && state.meds[0].source === "ocr" ? "photo (OCR)" : "pasted text";
  const patientLanguageLabel = PATIENT_LANGUAGE === "Kannada" ? "ಕನ್ನಡ" : "हिंदी";

  const doseStatusLabels: Record<string, string> = {
    idle: "No dose session running. Activate the plan, then jump to the evening dose.",
    calling: "Calling patient — awaiting voice turn.",
    completed: "Dose session complete. See packet and ledger.",
  };

  const lastAgentLine =
    state.transcript.length && state.transcript[state.transcript.length - 1].speaker === "agent"
      ? state.transcript[state.transcript.length - 1].text
      : "Listening…";
  const patientPrompt: Record<string, string> = {
    idle: "No dose scheduled right now.",
    calling: lastAgentLine,
    completed: "Sab set hai. Bheja gaya Ananya ko.",
  };
  const patientHint: Record<string, string> = {
    idle: "The caregiver will trigger the evening dose call.",
    calling: state.micBusy ? "Sun rahi hoon…" : "Tap the mic and reply when ready.",
    completed: "Information sent to your caregiver.",
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        fontFamily: "var(--font-body)",
      }}
    >
      <div style={{ width: "100%", maxWidth: 430, padding: "16px 16px 0", display: "flex", justifyContent: "center" }}>
        <div className="seg" role="radiogroup" aria-label="Preview role" style={{ width: "fit-content" }}>
          <label className="seg-opt">
            <input type="radio" name="previewRole" checked={isCaregiver} onChange={() => selectRole("caregiver")} />
            <CaregiverIcon />
            Caregiver view
          </label>
          <label className="seg-opt">
            <input type="radio" name="previewRole" checked={!isCaregiver} onChange={() => selectRole("patient")} />
            <PatientIcon />
            Patient view
          </label>
        </div>
      </div>

      <div
        style={{
          width: "100%",
          maxWidth: 430,
          minHeight: "100vh",
          background: "var(--color-bg)",
          display: "flex",
          flexDirection: "column",
          position: "relative",
        }}
      >
        {isCaregiver ? (
          <>
            <header
              style={{
                position: "sticky",
                top: 0,
                zIndex: 5,
                background: "var(--color-bg)",
                borderBottom: "1px solid var(--color-divider)",
                padding: "16px 18px 12px",
              }}
            >
              <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
                <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                  <span style={{ fontFamily: "var(--font-heading)", fontWeight: "var(--font-heading-weight)" as unknown as number, fontSize: 22, letterSpacing: ".01em" }}>
                    DAWA
                  </span>
                  <span style={{ fontSize: 11, opacity: 0.55 }}>Medication, executed.</span>
                </div>
                <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
                  <span title="API reachable" style={{ display: "inline-flex", alignItems: "center", gap: 5, fontSize: 11, opacity: 0.65 }}>
                    <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#3f7d4f", display: "inline-block" }} />
                    API
                  </span>
                  <button type="button" className="btn btn-ghost btn-icon" aria-label="Reset demo" onClick={resetDemo}>
                    <ResetIcon />
                  </button>
                </div>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
                <span className={`tag ${state.planStatus === "active" ? "tag-accent" : "tag-neutral"}`}>
                  {state.planStatus === "active" ? "active" : "draft"}
                </span>
                <span className="tag tag-neutral">Lakshmi · patient</span>
                <span className="tag tag-neutral">Ananya · caregiver</span>
              </div>
            </header>

            <main style={{ flex: 1, overflowY: "auto", padding: "18px 18px 90px" }}>
              {state.activeTab === "ingest" && (
                <div className="card">
                  <div className="card-kicker">1 · Ingest</div>
                  <div className="card-title">Bring in the discharge note</div>
                  <div className="seg" role="radiogroup" aria-label="Ingest mode" style={{ marginTop: 10 }}>
                    <label className="seg-opt">
                      <input
                        type="radio"
                        name="ingestMode"
                        checked={state.ingestMode === "paste"}
                        onChange={() => setState((s) => ({ ...s, ingestMode: "paste" as IngestMode }))}
                      />
                      <PasteIcon />
                      Paste text
                    </label>
                    <label className="seg-opt">
                      <input
                        type="radio"
                        name="ingestMode"
                        checked={state.ingestMode === "photo"}
                        onChange={() => setState((s) => ({ ...s, ingestMode: "photo" as IngestMode }))}
                      />
                      <PhotoIcon />
                      Upload photo
                    </label>
                  </div>

                  {state.ingestMode === "paste" && (
                    <div className="field" style={{ marginTop: 10 }}>
                      <label htmlFor="dawa-paste">Discharge text (Hindi/English mix OK)</label>
                      <textarea
                        id="dawa-paste"
                        className="input"
                        rows={7}
                        value={state.pasteText}
                        onChange={(e) => setState((s) => ({ ...s, pasteText: e.target.value }))}
                      />
                    </div>
                  )}
                  {state.ingestMode === "photo" && (
                    <div style={{ marginTop: 10 }}>
                      <div
                        onClick={() => fileInputRef.current?.click()}
                        style={{
                          width: "100%",
                          height: 180,
                          borderRadius: 10,
                          border: "1.5px dashed var(--color-divider)",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          textAlign: "center",
                          padding: 12,
                          cursor: "pointer",
                          overflow: "hidden",
                          background: "rgba(127,127,127,.08)",
                        }}
                      >
                        {state.photoDataUrl ? (
                          // eslint-disable-next-line @next/next/no-img-element
                          <img src={state.photoDataUrl} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                        ) : (
                          <span className="note" style={{ opacity: 0.75 }}>
                            Drop or click to upload prescription / discharge photo
                          </span>
                        )}
                      </div>
                      <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,application/pdf" hidden onChange={onPhotoChange} />
                      <p className="note" style={{ fontSize: 12, marginTop: 8 }}>
                        Sent to Sarvam Vision / Docs AI for OCR + extraction. Low-confidence fields still land in the med graph for human review below — the model never auto-activates a plan from a photo. Supported formats: {SARVAM_SUPPORTED_LABEL}.
                      </p>
                    </div>
                  )}

                  <button type="button" className="btn btn-primary btn-block" style={{ marginTop: 12 }} disabled={state.extracting} onClick={extract}>
                    {state.extracting ? (state.ingestMode === "photo" ? "Running Sarvam OCR…" : "Extracting…") : "Extract medications"}
                    <ArrowRightIcon />
                  </button>
                  {state.extractError && (
                    <p className="note" style={{ fontSize: 12, marginTop: 10, color: "#b3491f" }}>
                      {state.extractError}
                    </p>
                  )}
                  {state.meds.length > 0 && (
                    <p className="note" style={{ fontSize: 12, marginTop: 10 }}>
                      {state.meds.length} medications drafted from {extractSourceLabel}.{" "}
                      <a href="#meds" onClick={(e) => { e.preventDefault(); goToTab("meds"); }}>
                        Review medications →
                      </a>
                    </p>
                  )}
                </div>
              )}

              {state.activeTab === "meds" &&
                (state.meds.length > 0 ? (
                  <>
                    <div style={{ display: "grid", gap: 12 }}>
                      {state.meds.map((med) => (
                        <MedCard key={med.id} med={med} onDoseChange={onDoseChange} />
                      ))}
                    </div>
                    <label style={{ display: "flex", alignItems: "center", gap: 10, margin: "16px 2px", fontSize: 13 }}>
                      <input
                        type="checkbox"
                        checked={state.reviewed}
                        onChange={() => setState((s) => ({ ...s, reviewed: !s.reviewed }))}
                      />
                      I reviewed the medications above
                    </label>
                    <button
                      type="button"
                      className="btn btn-primary btn-block"
                      disabled={!state.reviewed || state.meds.length === 0}
                      onClick={confirmActivate}
                    >
                      Confirm &amp; Activate
                    </button>
                  </>
                ) : (
                  <p className="note" style={{ fontSize: 13 }}>
                    No medications yet. Go to{" "}
                    <a href="#ingest" onClick={(e) => { e.preventDefault(); goToTab("ingest"); }}>
                      Ingest
                    </a>{" "}
                    and extract from a discharge note first.
                  </p>
                ))}

              {state.activeTab === "dose" && (
                <>
                  <div className="card">
                    <div className="card-kicker">3 · Live dose</div>
                    <div className="card-title">Evening dose session</div>
                    <p className="card-body">{doseStatusLabels[state.doseStatus]}</p>
                    <button
                      type="button"
                      className="btn btn-primary btn-block"
                      style={{ marginTop: 10 }}
                      disabled={state.planStatus !== "active"}
                      onClick={jumpEvening}
                    >
                      Jump to evening dose
                    </button>
                    <p className="note" style={{ fontSize: 12, marginTop: 10 }}>
                      Patient session runs on the{" "}
                      <a href="#patient" onClick={(e) => { e.preventDefault(); selectRole("patient"); }}>
                        patient view
                      </a>{" "}
                      in {patientLanguageLabel}. Voice turns (STT/TTS) are Jyotir&apos;s runtime — this shell only hosts the mic slot and transcript.
                    </p>
                  </div>

                  <div className="hr" style={{ margin: "16px 0" }} />

                  <div className="card-kicker" style={{ padding: "0 2px" }}>
                    Live transcript
                  </div>
                  {state.transcript.length > 0 ? (
                    <div style={{ display: "grid", gap: 10, marginTop: 8 }}>
                      {state.transcript.map((line, i) => (
                        <div key={i} style={{ borderBottom: "1px solid var(--color-divider)", paddingBottom: 8 }}>
                          <div style={{ fontSize: 10, letterSpacing: ".08em", textTransform: "uppercase", opacity: 0.5 }}>
                            {speakerLabel(line.speaker)}
                          </div>
                          <div style={{ fontStyle: "italic", marginTop: 2 }}>{line.text}</div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="note" style={{ fontSize: 13, opacity: 0.55, marginTop: 8 }}>
                      No session yet.
                    </p>
                  )}

                  {DEV_MODE && (
                    <div style={{ marginTop: 20, border: "1px dashed var(--color-accent-600)", borderRadius: "var(--radius-md)", padding: 14 }}>
                      <span className="tag tag-outline" style={{ borderColor: "#b3491f", color: "#b3491f" }}>
                        DEV
                      </span>
                      <p className="note" style={{ fontSize: 12, margin: "8px 0" }}>
                        If voice runs late, complete the dose with the fixed side-effect outcome to keep the packet + ledger path demoable.
                      </p>
                      <button
                        type="button"
                        className="btn btn-secondary btn-block"
                        disabled={state.doseStatus !== "calling"}
                        onClick={simulateComplete}
                      >
                        Simulate complete (side effect)
                      </button>
                    </div>
                  )}
                </>
              )}

              {state.activeTab === "packet" &&
                (state.packet ? (
                  <PacketView packet={state.packet} />
                ) : (
                  <div className="card">
                    <p className="card-body" style={{ opacity: 0.6 }}>
                      No packet yet — complete a dose session to generate a caregiver alert card from the API.
                    </p>
                  </div>
                ))}

              {state.activeTab === "ledger" && (
                <>
                  <div className="card-kicker" style={{ padding: "0 2px" }}>
                    5 · Event ledger
                  </div>
                  {state.events.length > 0 ? (
                    <div style={{ marginTop: 8 }}>
                      {state.events
                        .slice()
                        .reverse()
                        .map((ev) => (
                          <div key={ev.id} style={{ display: "flex", gap: 12, borderBottom: "1px solid var(--color-divider)", padding: "10px 0" }}>
                            <div style={{ fontVariantNumeric: "tabular-nums", fontSize: 12, opacity: 0.55, whiteSpace: "nowrap" }}>
                              {ev.ts.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
                            </div>
                            <div>
                              <div style={{ fontSize: 13, fontWeight: 600 }}>{TYPE_LABELS[ev.type]}</div>
                              <div style={{ fontSize: 12, opacity: 0.65 }}>{ev.description}</div>
                            </div>
                          </div>
                        ))}
                    </div>
                  ) : (
                    <p className="note" style={{ fontSize: 13, opacity: 0.55, marginTop: 8 }}>
                      No events yet.
                    </p>
                  )}
                </>
              )}
            </main>

            <nav style={{ position: "sticky", bottom: 0, background: "var(--color-bg)", borderTop: "1px solid var(--color-divider)", display: "flex" }}>
              <button type="button" onClick={() => goToTab("ingest")} style={tabStyle(state.activeTab === "ingest")}>
                <IngestTabIcon />
                <span style={{ fontSize: 10 }}>Ingest</span>
              </button>
              <button type="button" onClick={() => goToTab("meds")} style={tabStyle(state.activeTab === "meds")}>
                <MedsTabIcon />
                <span style={{ fontSize: 10 }}>Meds</span>
              </button>
              <button type="button" onClick={() => goToTab("dose")} style={tabStyle(state.activeTab === "dose")}>
                <DoseTabIcon />
                <span style={{ fontSize: 10 }}>Dose</span>
              </button>
              <button type="button" onClick={() => goToTab("packet")} style={tabStyle(state.activeTab === "packet")}>
                <PacketTabIcon />
                <span style={{ fontSize: 10 }}>Packet</span>
              </button>
              <button type="button" onClick={() => goToTab("ledger")} style={tabStyle(state.activeTab === "ledger")}>
                <LedgerTabIcon />
                <span style={{ fontSize: 10 }}>Ledger</span>
              </button>
            </nav>
          </>
        ) : (
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "26px 22px 34px",
              textAlign: "center",
              minHeight: "100vh",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
              <span style={{ fontFamily: "var(--font-heading)", fontWeight: "var(--font-heading-weight)" as unknown as number, fontSize: 20 }}>
                DAWA
              </span>
              <span className="tag tag-neutral">{patientLanguageLabel}</span>
            </div>

            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 26 }}>
              <p style={{ fontFamily: "var(--font-heading)", fontSize: 24, lineHeight: 1.3, fontWeight: 400, maxWidth: 320, margin: 0 }}>
                {patientPrompt[state.doseStatus]}
              </p>

              <div style={{ position: "relative", width: 132, height: 132, display: "flex", alignItems: "center", justifyContent: "center" }}>
                {state.doseStatus === "calling" && !state.micBusy && (
                  <>
                    <div className="mic-ring" />
                    <div className="mic-ring r2" />
                  </>
                )}
                <button
                  type="button"
                  aria-label="Push to talk"
                  disabled={state.doseStatus !== "calling" || state.micBusy}
                  onClick={patientTapMic}
                  style={{
                    width: 96,
                    height: 96,
                    borderRadius: "50%",
                    border: "2px solid var(--color-accent-700)",
                    background: "transparent",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color: "var(--color-accent-700)",
                    cursor: state.doseStatus !== "calling" || state.micBusy ? "not-allowed" : "pointer",
                  }}
                >
                  <MicIcon />
                </button>
              </div>
              <p style={{ fontSize: 12, opacity: 0.55, maxWidth: 260, margin: 0 }}>{patientHint[state.doseStatus]}</p>
            </div>

            <div style={{ width: "100%", maxWidth: 300, display: "grid", gap: 8 }}>
              {state.transcript.map((line, i) => (
                <div key={i} style={{ textAlign: "left", borderTop: "1px solid var(--color-divider)", paddingTop: 6 }}>
                  <div style={{ fontSize: 9, letterSpacing: ".08em", textTransform: "uppercase", opacity: 0.5 }}>
                    {speakerLabel(line.speaker)}
                  </div>
                  <div style={{ fontSize: 13, fontStyle: "italic" }}>{line.text}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function MedCard({
  med,
  onDoseChange,
}: {
  med: Medication;
  onDoseChange: (id: string, val: number) => void;
}) {
  return (
    <div className="card" style={cardStyleFor(med.confidence)}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8 }}>
        <div className="card-title" style={{ fontSize: 17 }}>
          {med.name_raw}
        </div>
        <span className={`tag ${critTagClass(med.criticality)}`}>{med.criticality} criticality</span>
      </div>
      <p className="card-body" style={{ marginTop: 4 }}>
        {med.schedule_text} · {foodLabel(med.food_rule)}
      </p>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 8, flexWrap: "wrap" }}>
        <div className="field" style={{ margin: 0, maxWidth: 110 }}>
          <label htmlFor={`dose-${med.id}`}>Dose ({med.unit})</label>
          <input
            id={`dose-${med.id}`}
            className="input"
            type="number"
            value={med.dose}
            onChange={(e) => onDoseChange(med.id, Number(e.target.value))}
          />
        </div>
        <span className="card-meta" style={{ margin: 0 }}>
          confidence {Math.round(med.confidence * 100)}%
        </span>
      </div>
    </div>
  );
}

function PacketView({ packet }: { packet: CarePacket }) {
  return (
    <>
      <div className="card elev-md">
        <div className="card-kicker">4 · Caregiver packet</div>
        <div className="card-title">{packet.medication}</div>
        <div style={{ display: "flex", gap: 8, margin: "8px 0" }}>
          <span className="tag tag-accent">{packet.status}</span>
          <span className="tag tag-outline">side effect · {packet.exception.normalized}</span>
        </div>
        <p className="card-body">
          Patient said: <em>&ldquo;{packet.exception.patient_reported}&rdquo;</em> — normalized as {packet.exception.normalized}.
        </p>
        <div className="hr" style={{ margin: "10px 0" }} />
        <div className="card-kicker">System action</div>
        <p className="card-body">{packet.system_action}</p>
        <div className="card-kicker" style={{ marginTop: 8 }}>
          Suggested for caregiver
        </div>
        <ul style={{ margin: "6px 0 0", paddingLeft: 18, fontFamily: "var(--font-body)" }}>
          {packet.suggested_caregiver_actions.map((s, i) => (
            <li key={i} style={{ marginBottom: 4 }}>
              {s}
            </li>
          ))}
        </ul>
        <div className="card-meta" style={{ marginTop: 10 }}>
          Confidence {Math.round(packet.confidence * 100)}% · {packet.language} ·{" "}
          {packet.needs_clinician ? "needs clinician" : "no clinician needed"}
        </div>
      </div>
      <div style={{ textAlign: "center", padding: "22px 10px 6px" }}>
        <p style={{ fontFamily: "var(--font-heading)", fontStyle: "italic", fontSize: 19, fontWeight: 400, margin: 0 }}>
          &ldquo;She took the medicine. The family finally knows what changed.&rdquo;
        </p>
        <p style={{ fontSize: 12, opacity: 0.6, marginTop: 8 }}>Discharge is not the end of care. Execution is.</p>
      </div>
    </>
  );
}
