"use client";

import { useRef, useState } from "react";
import {
  extractPlan,
  getEvents,
  getLatestPacket,
  resetWorld,
  runDisasterFallback,
  saveAndActivatePlan,
  startVoiceSession,
  triggerDose,
} from "./api";
import { initialState } from "./demoData";
import {
  ArrowRightIcon,
  DoseTabIcon,
  IngestTabIcon,
  LedgerTabIcon,
  MedsTabIcon,
  PacketTabIcon,
  PasteIcon,
  PhotoIcon,
  ResetIcon,
} from "./icons";
import {
  CarePacket,
  CockpitState,
  Criticality,
  FoodRule,
  IngestMode,
  LedgerEvent,
  LedgerEventType,
  Medication,
  Tab,
} from "./types";

const DEV_MODE = process.env.NEXT_PUBLIC_DEV_MODE === "1";
const SARVAM_SUPPORTED_TYPES = new Set(["image/jpeg", "image/png", "application/pdf"]);
const SARVAM_SUPPORTED_LABEL = "JPEG, PNG, or PDF";

const TYPE_LABELS: Record<LedgerEventType, string> = {
  plan_created: "Plan created",
  plan_activated: "Plan activated",
  dose_triggered: "Dose call triggered",
  dose_started: "Patient answered",
  dose_completed: "Dose completed",
  exception_logged: "Exception logged",
  packet_sent: "Caregiver packet sent",
  policy_refused: "Unsafe action refused",
};

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

const confClass = (confidence: number) =>
  confidence < 0.8 ? "error" : confidence < 0.87 ? "warn" : "ok";
const cardStyleFor = (confidence: number): React.CSSProperties => {
  const kind = confClass(confidence);
  if (kind === "error") return { borderColor: "#b3491f" };
  if (kind === "warn") return { borderColor: "var(--color-accent-600)" };
  return {};
};
const critTagClass = (criticality: Criticality) =>
  criticality === "high" ? "tag-accent" : criticality === "med" ? "tag-outline" : "tag-neutral";
const foodLabel = (foodRule: FoodRule) =>
  foodRule === "with_food" ? "with food" : foodRule === "none" ? "no food rule" : foodRule;

function eventDescription(event: LedgerEvent): string {
  const payload = event.payload;
  switch (event.type) {
    case "plan_created":
      return `${String(payload.medication_count ?? 0)} medications extracted`;
    case "dose_triggered":
      return String(payload.medication_name ?? "Evening medication");
    case "dose_completed":
      return `${String(payload.adherence ?? "recorded")} · ${String(payload.exception_type ?? "none")}`;
    case "exception_logged":
      return String(payload.normalized_symptom ?? payload.exception_type ?? "Patient-reported exception");
    case "packet_sent":
      return "Structured English update sent to Ananya";
    case "policy_refused":
      return String(payload.reason ?? "Unsafe medication action refused");
    default:
      return TYPE_LABELS[event.type];
  }
}

export default function CockpitApp() {
  const [state, setState] = useState<CockpitState>(initialState);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const goToTab = (activeTab: Tab) => setState((current) => ({ ...current, activeTab }));
  const fail = (error: unknown) => {
    const message = error instanceof Error ? error.message : "Something went wrong";
    setState((current) => ({ ...current, busy: false, error: message }));
  };

  const extract = async () => {
    const source = state.ingestMode === "photo" ? "ocr" : "paste";
    if (source === "ocr" && !state.photoFile) {
      setState((current) => ({ ...current, error: "Upload a photo first." }));
      return;
    }
    setState((current) => ({ ...current, busy: true, error: null }));
    try {
      const result = await extractPlan({
        source,
        text: source === "paste" ? state.pasteText : undefined,
        file: source === "ocr" ? state.photoFile || undefined : undefined,
      });
      const events = await getEvents(result.plan_id);
      setState((current) => ({
        ...current,
        busy: false,
        planId: result.plan_id,
        planStatus: result.status,
        reviewed: false,
        meds: result.medications,
        events,
        error: null,
        activeTab: "meds",
      }));
    } catch (error) {
      fail(error);
    }
  };

  const onDoseChange = (id: string, dose: number) => {
    setState((current) => ({
      ...current,
      meds: current.meds.map((medication) =>
        medication.id === id ? { ...medication, dose } : medication,
      ),
    }));
  };

  const confirmActivate = async () => {
    if (!state.planId || !state.reviewed || state.meds.length === 0) return;
    setState((current) => ({ ...current, busy: true, error: null }));
    try {
      await saveAndActivatePlan(state.planId, state.meds);
      const events = await getEvents(state.planId);
      setState((current) => ({
        ...current,
        busy: false,
        planStatus: "active",
        events,
        activeTab: "dose",
      }));
    } catch (error) {
      fail(error);
    }
  };

  const startCall = async () => {
    if (!state.planId || state.planStatus !== "active") return;
    setState((current) => ({ ...current, busy: true, error: null }));
    try {
      const dose = await triggerDose(state.planId);
      const voice = await startVoiceSession(dose.dose_id, dose.medication);
      const events = await getEvents(state.planId);
      setState((current) => ({
        ...current,
        busy: false,
        doseId: dose.dose_id,
        doseStatus: "calling",
        voiceSessionId: voice.session_id,
        transcript: voice.turns,
        events,
      }));
    } catch (error) {
      fail(error);
    }
  };

  const refreshOutcome = async () => {
    if (!state.planId) return;
    setState((current) => ({ ...current, busy: true, error: null }));
    try {
      const events = await getEvents(state.planId);
      let packet: CarePacket | null = null;
      try {
        packet = await getLatestPacket(state.planId);
      } catch {
        // A packet only exists after an exception; the ledger remains authoritative.
      }
      const completed = events.some(
        (event) => event.type === "dose_completed" && (!state.doseId || event.dose_id === state.doseId),
      );
      setState((current) => ({
        ...current,
        busy: false,
        events,
        packet,
        doseStatus: completed ? "completed" : current.doseStatus,
        activeTab: packet ? "packet" : current.activeTab,
      }));
    } catch (error) {
      fail(error);
    }
  };

  const simulateVoiceOutcome = async () => {
    if (!state.voiceSessionId || !state.planId) return;
    setState((current) => ({ ...current, busy: true, error: null }));
    try {
      const voice = await runDisasterFallback(state.voiceSessionId);
      if (!voice.complete_posted) {
        throw new Error(voice.complete_error || "Voice finished but the backend completion write failed");
      }
      const [events, packet] = await Promise.all([
        getEvents(state.planId),
        getLatestPacket(state.planId),
      ]);
      setState((current) => ({
        ...current,
        busy: false,
        doseStatus: "completed",
        transcript: voice.turns,
        events,
        packet,
        activeTab: "packet",
      }));
    } catch (error) {
      fail(error);
    }
  };

  const resetDemo = async () => {
    setState((current) => ({ ...current, busy: true, error: null }));
    try {
      await resetWorld();
      setState(initialState());
    } catch (error) {
      fail(error);
    }
  };

  const onPhotoChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    if (!SARVAM_SUPPORTED_TYPES.has(file.type)) {
      setState((current) => ({
        ...current,
        error: `Only ${SARVAM_SUPPORTED_LABEL} files are supported.`,
      }));
      event.target.value = "";
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      setState((current) => ({
        ...current,
        photoDataUrl: String(reader.result),
        photoFile: file,
        error: null,
      }));
    };
    reader.readAsDataURL(file);
  };

  const doseStatusText = {
    idle: "Activate the plan, then start the evening dose call.",
    calling: "Voice session started for Lakshmi. Waiting for the phone-agent outcome.",
    completed: "Dose outcome recorded. The packet and ledger came from the backend.",
  }[state.doseStatus];

  return (
    <div style={{ minHeight: "100vh", display: "flex", justifyContent: "center", fontFamily: "var(--font-body)" }}>
      <div style={{ width: "100%", maxWidth: 430, minHeight: "100vh", background: "var(--color-bg)", display: "flex", flexDirection: "column" }}>
        <header style={{ position: "sticky", top: 0, zIndex: 5, background: "var(--color-bg)", borderBottom: "1px solid var(--color-divider)", padding: "16px 18px 12px" }}>
          <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
              <span style={{ fontFamily: "var(--font-heading)", fontWeight: 600, fontSize: 22 }}>DAWA</span>
              <span style={{ fontSize: 11, opacity: 0.55 }}>Caregiver cockpit</span>
            </div>
            <button type="button" className="btn btn-ghost btn-icon" aria-label="Reset demo" disabled={state.busy} onClick={resetDemo}>
              <ResetIcon />
            </button>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10, flexWrap: "wrap" }}>
            <span className={`tag ${state.planStatus === "active" ? "tag-accent" : "tag-neutral"}`}>{state.planStatus}</span>
            <span className="tag tag-neutral">Lakshmi · phone only · Hindi</span>
            <span className="tag tag-neutral">Ananya · caregiver</span>
          </div>
          {state.error && <p style={{ color: "#b3491f", fontSize: 12, margin: "10px 0 0" }}>{state.error}</p>}
        </header>

        <main style={{ flex: 1, overflowY: "auto", padding: "18px 18px 90px" }}>
          {state.activeTab === "ingest" && (
            <div className="card">
              <div className="card-kicker">1 · Ingest</div>
              <div className="card-title">Bring in the discharge note</div>
              <div className="seg" role="radiogroup" aria-label="Ingest mode" style={{ marginTop: 10 }}>
                <label className="seg-opt">
                  <input type="radio" name="ingestMode" checked={state.ingestMode === "paste"} onChange={() => setState((current) => ({ ...current, ingestMode: "paste" as IngestMode }))} />
                  <PasteIcon /> Paste text
                </label>
                <label className="seg-opt">
                  <input type="radio" name="ingestMode" checked={state.ingestMode === "photo"} onChange={() => setState((current) => ({ ...current, ingestMode: "photo" as IngestMode }))} />
                  <PhotoIcon /> Upload photo
                </label>
              </div>
              {state.ingestMode === "paste" ? (
                <div className="field" style={{ marginTop: 10 }}>
                  <label htmlFor="dawa-paste">Discharge text (Hindi/English mix OK)</label>
                  <textarea id="dawa-paste" className="input" rows={7} value={state.pasteText} onChange={(event) => setState((current) => ({ ...current, pasteText: event.target.value }))} />
                </div>
              ) : (
                <div style={{ marginTop: 10 }}>
                  <button type="button" className="btn btn-secondary btn-block" onClick={() => fileInputRef.current?.click()}>
                    {state.photoFile ? state.photoFile.name : "Choose prescription photo or PDF"}
                  </button>
                  <input ref={fileInputRef} type="file" accept="image/jpeg,image/png,application/pdf" hidden onChange={onPhotoChange} />
                  <p className="note">Sarvam Doc AI accepts {SARVAM_SUPPORTED_LABEL}. Human confirmation is still required.</p>
                </div>
              )}
              <button type="button" className="btn btn-primary btn-block" disabled={state.busy} onClick={extract}>
                {state.busy ? "Working…" : "Extract medications"} <ArrowRightIcon />
              </button>
            </div>
          )}

          {state.activeTab === "meds" && (
            state.meds.length ? (
              <>
                <div style={{ display: "grid", gap: 12 }}>
                  {state.meds.map((medication) => <MedCard key={medication.id} med={medication} onDoseChange={onDoseChange} />)}
                </div>
                <label style={{ display: "flex", alignItems: "center", gap: 10, margin: "16px 2px", fontSize: 13 }}>
                  <input type="checkbox" checked={state.reviewed} onChange={() => setState((current) => ({ ...current, reviewed: !current.reviewed }))} />
                  I reviewed the medication plan
                </label>
                <button type="button" className="btn btn-primary btn-block" disabled={state.busy || !state.reviewed} onClick={confirmActivate}>
                  {state.busy ? "Activating…" : "Confirm & Activate"}
                </button>
              </>
            ) : <EmptyState text="Extract a discharge note first." target="ingest" goToTab={goToTab} />
          )}

          {state.activeTab === "dose" && (
            <>
              <div className="card">
                <div className="card-kicker">3 · Patient voice call</div>
                <div className="card-title">Evening Amlodipine check-in</div>
                <p className="card-body">{doseStatusText}</p>
                <button type="button" className="btn btn-primary btn-block" disabled={state.busy || state.planStatus !== "active" || state.doseStatus === "calling"} onClick={startCall}>
                  {state.busy ? "Starting…" : "Call Lakshmi"}
                </button>
                {state.doseStatus === "calling" && (
                  <button type="button" className="btn btn-secondary btn-block" disabled={state.busy} onClick={refreshOutcome}>Refresh call outcome</button>
                )}
                <p className="note" style={{ marginTop: 10 }}>
                  Lakshmi uses only her phone. There is deliberately no patient web screen.
                </p>
              </div>
              {DEV_MODE && state.doseStatus === "calling" && (
                <div style={{ marginTop: 18, border: "1px dashed #b3491f", borderRadius: 4, padding: 14 }}>
                  <span className="tag tag-outline" style={{ borderColor: "#b3491f", color: "#b3491f" }}>DISASTER FALLBACK</span>
                  <p className="note">Runs the fixed Hindi transcript through Jyotir&apos;s real classifier and Barkha&apos;s real completion endpoint. Never use as the judged happy path.</p>
                  <button type="button" className="btn btn-secondary btn-block" disabled={state.busy} onClick={simulateVoiceOutcome}>Simulate failed telephony only</button>
                </div>
              )}
            </>
          )}

          {state.activeTab === "packet" && (
            state.packet ? <PacketView packet={state.packet} /> : <EmptyState text="No caregiver packet yet. Complete a side-effect call first." target="dose" goToTab={goToTab} />
          )}

          {state.activeTab === "ledger" && (
            <>
              <div className="card-kicker">5 · Backend event ledger</div>
              {state.events.length ? (
                <div style={{ marginTop: 8 }}>
                  {[...state.events].reverse().map((event) => (
                    <div key={event.id} style={{ display: "flex", gap: 12, borderBottom: "1px solid var(--color-divider)", padding: "10px 0" }}>
                      <div style={{ fontVariantNumeric: "tabular-nums", fontSize: 12, opacity: 0.55, whiteSpace: "nowrap" }}>
                        {new Date(event.ts).toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
                      </div>
                      <div>
                        <div style={{ fontSize: 13, fontWeight: 600 }}>{TYPE_LABELS[event.type]}</div>
                        <div style={{ fontSize: 12, opacity: 0.65 }}>{eventDescription(event)}</div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : <EmptyState text="No backend events yet." target="ingest" goToTab={goToTab} />}
            </>
          )}
        </main>

        <nav style={{ position: "sticky", bottom: 0, background: "var(--color-bg)", borderTop: "1px solid var(--color-divider)", display: "flex" }}>
          <NavButton label="Ingest" active={state.activeTab === "ingest"} onClick={() => goToTab("ingest")} icon={<IngestTabIcon />} />
          <NavButton label="Meds" active={state.activeTab === "meds"} onClick={() => goToTab("meds")} icon={<MedsTabIcon />} />
          <NavButton label="Call" active={state.activeTab === "dose"} onClick={() => goToTab("dose")} icon={<DoseTabIcon />} />
          <NavButton label="Packet" active={state.activeTab === "packet"} onClick={() => goToTab("packet")} icon={<PacketTabIcon />} />
          <NavButton label="Ledger" active={state.activeTab === "ledger"} onClick={() => goToTab("ledger")} icon={<LedgerTabIcon />} />
        </nav>
      </div>
    </div>
  );
}

function NavButton({ label, active, onClick, icon }: { label: string; active: boolean; onClick: () => void; icon: React.ReactNode }) {
  return <button type="button" onClick={onClick} style={tabStyle(active)}>{icon}<span style={{ fontSize: 10 }}>{label}</span></button>;
}

function EmptyState({ text, target, goToTab }: { text: string; target: Tab; goToTab: (tab: Tab) => void }) {
  return <div className="card"><p className="card-body" style={{ opacity: 0.6 }}>{text}</p><button type="button" className="btn btn-secondary" onClick={() => goToTab(target)}>Go to {target}</button></div>;
}

function MedCard({ med, onDoseChange }: { med: Medication; onDoseChange: (id: string, value: number) => void }) {
  return (
    <div className="card" style={cardStyleFor(med.confidence)}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8 }}>
        <div className="card-title" style={{ fontSize: 17 }}>{med.name_raw}</div>
        <span className={`tag ${critTagClass(med.criticality)}`}>{med.criticality} criticality</span>
      </div>
      <p className="card-body">{med.schedule_text} · {foodLabel(med.food_rule)}</p>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 8, flexWrap: "wrap" }}>
        <div className="field" style={{ margin: 0, maxWidth: 110 }}>
          <label htmlFor={`dose-${med.id}`}>Dose ({med.unit})</label>
          <input id={`dose-${med.id}`} className="input" type="number" value={med.dose} onChange={(event) => onDoseChange(med.id, Number(event.target.value))} />
        </div>
        <span className="card-meta">confidence {Math.round(med.confidence * 100)}%</span>
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
        <div style={{ display: "flex", gap: 8, margin: "8px 0", flexWrap: "wrap" }}>
          <span className="tag tag-accent">{packet.status}</span>
          <span className="tag tag-outline">{packet.exception.type} · {packet.exception.normalized || "unclassified"}</span>
        </div>
        <p className="card-body">Patient said: <em>&ldquo;{packet.exception.patient_reported || "No detail captured"}&rdquo;</em></p>
        <div className="hr" style={{ margin: "10px 0" }} />
        <div className="card-kicker">System action</div>
        <p className="card-body">{packet.system_action}</p>
        <div className="card-kicker" style={{ marginTop: 8 }}>Suggested for caregiver</div>
        <ul style={{ margin: "6px 0 0", paddingLeft: 18 }}>
          {packet.suggested_caregiver_actions.map((action) => <li key={action} style={{ marginBottom: 4 }}>{action}</li>)}
        </ul>
        <div className="card-meta" style={{ marginTop: 10 }}>
          Confidence {Math.round(packet.confidence * 100)}% · {packet.language} · {packet.needs_clinician ? "needs clinician" : "no clinician needed"}
        </div>
      </div>
      <div style={{ textAlign: "center", padding: "22px 10px 6px" }}>
        <p style={{ fontFamily: "var(--font-heading)", fontStyle: "italic", fontSize: 19, margin: 0 }}>&ldquo;She took the medicine. The family finally knows what changed.&rdquo;</p>
        <p style={{ fontSize: 12, opacity: 0.6, marginTop: 8 }}>Discharge is not the end of care. Execution is.</p>
      </div>
    </>
  );
}
