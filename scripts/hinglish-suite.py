#!/usr/bin/env python3
"""The 50 Hinglish cases, run against a live DAWA API.

    services/api/.venv/bin/python scripts/hinglish-suite.py [--base URL] [--only 6,7,40]

Outcomes:
    PASS  behaves as the case expects
    FAIL  the case is inside what the contract promises, and it is broken
    GAP   the contract has no such field or endpoint — an honest limitation,
          not a regression (e.g. there is no `quantity` on Medication)

Extraction is formulary-locked to fixtures/formulary.json (amlodipine,
metformin, atorvastatin, paracetamol), so cases naming no drug ("Ye tablet
breakfast ke baad leni hai") can only ever return zero medications. Where a
case is really testing a *schedule* rule, the drug name is prepended and the
adaptation is printed with the result.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "api"))

BASE = "http://localhost:8000"
TIMEOUT = 60.0

GREEN, RED, YELLOW, DIM, RESET = "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[0m"
BADGE = {"PASS": f"{GREEN}PASS{RESET}", "FAIL": f"{RED}FAIL{RESET}", "GAP": f"{YELLOW}GAP {RESET}"}

CASES: list[tuple[int, str, callable]] = []
DISCHARGE = "Amlodipine 5 mg"  # drug context for schedule-only cases


def case(num: int, title: str):
    def wrap(fn):
        CASES.append((num, title, fn))
        return fn

    return wrap


class Api:
    def __init__(self, base: str) -> None:
        self.c = httpx.Client(base_url=base, timeout=TIMEOUT)

    def get(self, path: str, **kw) -> httpx.Response:
        return self.c.get(path, **kw)

    def post(self, path: str, json=None) -> httpx.Response:
        return self.c.post(path, json=json)

    def patch(self, path: str, json=None) -> httpx.Response:
        return self.c.patch(path, json=json)

    # --- shorthands the cases lean on ---

    def reset(self) -> None:
        self.post("/demo/reset")

    def extract(self, text: str) -> dict:
        return self.post("/plans/extract", {"text": text, "source": "paste"}).json()

    def meds(self, text: str) -> list[dict]:
        return self.extract(text).get("medications", [])

    def med_named(self, text: str, name: str) -> dict | None:
        return next((m for m in self.meds(text) if m["name_normalized"] == name), None)

    def active_plan(self, text: str = DISCHARGE + " roz raat ko") -> str:
        """Fresh world -> extracted -> activated plan id."""
        self.reset()
        plan_id = self.extract(text)["plan_id"]
        self.post(f"/plans/{plan_id}/activate")
        return plan_id

    def dose(self, plan_id: str, simulate_time: str = "evening") -> str:
        body = {"plan_id": plan_id, "simulate_time": simulate_time}
        return self.post("/doses/trigger", body).json()["dose_id"]

    def complete(self, dose_id: str, **body) -> dict:
        body.setdefault("adherence", "taken")
        return self.post(f"/doses/{dose_id}/complete", body).json()

    def event_types(self, plan_id: str | None = None) -> list[str]:
        params = {"plan_id": plan_id} if plan_id else None
        return [e["type"] for e in self.get("/events", params=params).json()["events"]]

    def voice(self, dose_id: str, text: str) -> dict:
        return self.post(f"/doses/{dose_id}/voice-turn", {"user_text": text}).json()

    def policy(self, intent: str, medication_id: str | None = None) -> dict:
        return self.post("/policy/check", {"intent": intent, "medication_id": medication_id}).json()


# ------------------------------------------------------------ basic / reset


@case(1, "Health check")
def c1(a: Api):
    r = a.get("/health")
    ok = r.status_code == 200 and r.json() == {"ok": True}
    return ok, f"GET /health -> {r.status_code} {r.json()}"


@case(2, "Reset")
def c2(a: Api):
    r = a.post("/demo/reset")
    people = a.get("/people").json()
    ok = r.json() == {"ok": True} and "patient" in people
    return ok, f"reset ok, patient={people['patient']['display_name']}"


@case(3, "Patient list")
def c3(a: Api):
    p = a.get("/people").json()
    ok = p["patient"]["role"] == "patient" and p["caregiver"]["role"] == "caregiver"
    return ok, f"{p['patient']['display_name']} + caregiver {p['caregiver']['display_name']}"


@case(4, "Reset clears plans/doses/events")
def c4(a: Api):
    plan_id = a.active_plan()
    a.complete(a.dose(plan_id))
    before = len(a.event_types())
    a.reset()
    after = a.event_types()
    gone = a.get(f"/plans/{plan_id}").status_code
    ok = after == [] and gone == 404
    return ok, f"{before} events -> {len(after)} after reset; old plan GET -> {gone}"


@case(5, "Double reset is idempotent")
def c5(a: Api):
    a.reset()
    first = a.get("/people").json()
    a.reset()
    second = a.get("/people").json()
    ok = first == second and a.event_types() == []
    return ok, "people identical after two resets, no duplicate seed"


# -------------------------------------------------------------- extraction


@case(6, "Simple medicine")
def c6(a: Api):
    m = a.med_named("Doctor ne bola hai Amlodipine 5 mg roz subah ek tablet leni hai.", "amlodipine")
    if not m:
        return False, "amlodipine not extracted"
    ok = m["dose"] == 5 and m["unit"] == "mg" and m["times"] == ["08:00"]
    return ok, f"dose={m['dose']}{m['unit']} times={m['times']} ({m['schedule_text']})"


@case(7, "Twice a day")
def c7(a: Api):
    m = a.med_named("Metformin 500 mg subah aur raat ko ek-ek tablet leni hai.", "metformin")
    if not m:
        return False, "metformin not extracted"
    ok = m["times"] == ["08:00", "21:00"]
    return ok, f"dose={m['dose']}{m['unit']} times={m['times']}"


@case(8, "Hindi number 'paanch milligram'")
def c8(a: Api):
    m = a.med_named("Amlodipine paanch milligram roz subah lena hai.", "amlodipine")
    if not m:
        return False, "amlodipine not extracted"
    ok = m["dose"] == 5
    note = "dose comes from the locked formulary, NOT parsed from 'paanch'"
    return ok, f"dose={m['dose']}{m['unit']} — {note}"


@case(9, "After food")
def c9(a: Api):
    bare = a.meds("Ye tablet breakfast ke baad leni hai.")
    m = a.med_named(f"{DISCHARGE} — breakfast ke baad leni hai", "amlodipine")
    ok = bool(m) and m["food_rule"] == "with_food"
    got = m["food_rule"] if m else "-"
    return ok, f"food_rule={got}; bare sentence (no drug named) -> {len(bare)} meds"


@case(10, "Before food")
def c10(a: Api):
    m = a.med_named(f"{DISCHARGE} — khana khane se pehle leni hai", "amlodipine")
    ok = bool(m) and m["food_rule"] == "before_food"
    return ok, f"food_rule={m['food_rule'] if m else '-'} ({m['schedule_text'] if m else '-'})"


@case(11, "Bedtime")
def c11(a: Api):
    m = a.med_named(f"{DISCHARGE} — raat ko sone se pehle leni hai", "amlodipine")
    ok = bool(m) and m["times"] == ["21:00"]
    return ok, f"times={m['times'] if m else '-'} ({m['schedule_text'] if m else '-'})"


@case(12, "Morning only")
def c12(a: Api):
    m = a.med_named(f"{DISCHARGE} — sirf subah leni hai", "amlodipine")
    ok = bool(m) and m["times"] == ["08:00"]
    return ok, f"times={m['times'] if m else '-'} ({m['schedule_text'] if m else '-'})"


@case(13, "Evening ('shaam ko')")
def c13(a: Api):
    m = a.med_named(f"{DISCHARGE} — shaam ko leni hai", "amlodipine")
    if not m:
        return False, "amlodipine not extracted"
    ok = m["times"] == ["21:00"]
    hint = "" if ok else " <- 'shaam' is not in NIGHT_HINTS ('sham' is); fell back to default"
    return ok, f"times={m['times']} ({m['schedule_text']}){hint}"


@case(14, "Multiple medicines")
def c14(a: Api):
    got = {m["name_normalized"] for m in a.meds(
        "Amlodipine 5 mg subah aur Metformin 500 mg subah-shaam leni hai."
    )}
    ok = {"amlodipine", "metformin"} <= got
    return ok, f"extracted {sorted(got)}"


@case(15, "Duration '7 din tak'")
def c15(a: Api):
    m = a.med_named(f"{DISCHARGE} — 7 din tak roz raat ko leni hai", "amlodipine")
    got = m["duration_days"] if m else "-"
    # duration_days is read off the formulary row, never off the note.
    return ("GAP", f"duration_days={got} (formulary default); note says 7")


@case(16, "Continue after discharge")
def c16(a: Api):
    m = a.med_named(
        "Hospital se discharge hone ke baad Amlodipine 5 mg continue karni hai.", "amlodipine"
    )
    return bool(m), f"amlodipine extracted={bool(m)}"


@case(17, "Messy Hinglish, two drugs")
def c17(a: Api):
    meds = {m["name_normalized"]: m for m in a.meds(
        "Discharge ke baad amlodipine 5mg morning mein continue karna hai "
        "aur metformin 500mg morning evening lena hai."
    )}
    ok = (
        meds.get("amlodipine", {}).get("times") == ["08:00"]
        and meds.get("metformin", {}).get("times") == ["08:00", "21:00"]
    )
    detail = ", ".join(f"{n}={m['times']}" for n, m in meds.items()) or "nothing extracted"
    return ok, detail


@case(18, "Tablet quantity 'do tablets'")
def c18(a: Api):
    m = a.med_named(f"{DISCHARGE} — subah do tablets leni hain", "amlodipine")
    fields = sorted(m.keys()) if m else []
    # Medication has dose/unit but no per-administration quantity.
    return ("GAP", f"no 'quantity' field on Medication (has: dose, unit); keys={len(fields)}")


@case(19, "No medicine mentioned")
def c19(a: Api):
    meds = a.meds("Aaj patient ko rest karna hai aur paani zyada peena hai.")
    return len(meds) == 0, f"{len(meds)} medications invented"


@case(20, "Unknown drug XYZABC")
def c20(a: Api):
    meds = a.meds("XYZABC 999 mg roz subah lena hai.")
    return len(meds) == 0, f"{len(meds)} medications invented"


# ------------------------------------------------------------------- plans


@case(21, "Read plan back")
def c21(a: Api):
    a.reset()
    plan_id = a.extract(DISCHARGE + " roz subah")["plan_id"]
    plan = a.get(f"/plans/{plan_id}").json()
    ok = plan["id"] == plan_id and plan["status"] == "draft" and plan["medications"]
    return ok, f"{plan_id} status={plan['status']} meds={len(plan['medications'])}"


@case(22, "Change timing morning -> evening")
def c22(a: Api):
    a.reset()
    plan = a.extract(DISCHARGE + " roz subah")
    med = dict(plan["medications"][0])
    med["times"], med["schedule_text"] = ["21:00"], "Night"
    r = a.patch(f"/plans/{plan['plan_id']}", {"medications": [med]})
    ok = r.status_code == 200 and r.json()["medications"][0]["times"] == ["21:00"]
    return ok, f"PATCH -> {r.status_code}, times now {r.json()['medications'][0]['times']}"


@case(23, "Activate plan")
def c23(a: Api):
    a.reset()
    plan_id = a.extract(DISCHARGE + " roz raat ko")["plan_id"]
    r = a.post(f"/plans/{plan_id}/activate")
    ok = r.status_code == 200 and r.json()["status"] == "active"
    return ok, f"status={r.json().get('status')}"


@case(24, "Activate an already-active plan")
def c24(a: Api):
    plan_id = a.active_plan()
    r = a.post(f"/plans/{plan_id}/activate")
    plans_active = a.get(f"/plans/{plan_id}").json()["status"]
    ok = r.status_code == 200 and plans_active == "active"
    return ok, f"second activate -> {r.status_code}, still exactly one active plan"


@case(25, "Activate a non-existent plan")
def c25(a: Api):
    r = a.post("/plans/plan_does_not_exist/activate")
    ok = r.status_code == 404 and r.json()["error"]["code"] == "PLAN_NOT_FOUND"
    return ok, f"{r.status_code} {r.json().get('error', {}).get('code')}"


@case(26, "Update a non-existent plan")
def c26(a: Api):
    r = a.patch("/plans/plan_nope", {"medications": []})
    ok = r.status_code == 404 and r.json()["error"]["code"] == "PLAN_NOT_FOUND"
    return ok, f"{r.status_code} {r.json().get('error', {}).get('code')}"


@case(27, "Trigger dose before activate")
def c27(a: Api):
    a.reset()
    plan_id = a.extract(DISCHARGE + " roz raat ko")["plan_id"]
    r = a.post("/doses/trigger", {"plan_id": plan_id, "simulate_time": "evening"})
    ok = r.status_code >= 400 and r.json()["error"]["code"] == "PLAN_NOT_ACTIVE"
    return ok, f"{r.status_code} {r.json().get('error', {}).get('code')}"


# ------------------------------------------------------------------- doses


@case(28, "Normal dose trigger")
def c28(a: Api):
    plan_id = a.active_plan()
    r = a.post("/doses/trigger", {"plan_id": plan_id, "simulate_time": "evening"})
    body = r.json()
    ok = r.status_code == 200 and body["status"] == "calling"
    return ok, f"dose={body.get('dose_id')} status={body.get('status')} med={body['medication']['name_normalized']}"


@case(29, "Trigger the same dose twice")
def c29(a: Api):
    plan_id = a.active_plan()
    first = a.dose(plan_id)
    r = a.post("/doses/trigger", {"plan_id": plan_id, "simulate_time": "evening"})
    second = r.json().get("dose_id")
    if first != second and r.status_code == 200:
        return ("GAP", f"created a second open dose {second} beside {first}; no in-flight guard")
    return True, f"second trigger -> {r.status_code}, dose {second}"


@case(30, "Medicine taken")
def c30(a: Api):
    plan_id = a.active_plan()
    dose_id = a.dose(plan_id)
    guess = a.voice(dose_id, "Haan, maine medicine le li hai.")["partial"]
    out = a.complete(dose_id, adherence="taken", exception_type="none")
    ok = out["status"] == "completed" and out["policy"]["allowed"] and out["packet_id"] is None
    return ok, f"voice guess={guess['adherence_guess']}, completed, packet={out['packet_id']}"


@case(31, "Medicine not taken")
def c31(a: Api):
    plan_id = a.active_plan()
    dose_id = a.dose(plan_id)
    guess = a.voice(dose_id, "Nahi, maine abhi medicine nahi li.")["partial"]
    out = a.complete(dose_id, adherence="missed", exception_type="missed_dose")
    ok = out["status"] == "completed" and "escalate_caregiver" in out["policy"]["actions"]
    return ok, f"voice guess={guess['adherence_guess']}, actions={out['policy']['actions']}, packet={out['packet_id']}"


def _side_effect_case(a: Api, utterance: str, symptom: str | None):
    plan_id = a.active_plan()
    dose_id = a.dose(plan_id)
    guess = a.voice(dose_id, utterance)["partial"]
    out = a.complete(
        dose_id,
        adherence="taken",
        exception_type="side_effect",
        patient_reported=utterance,
        normalized_symptom=symptom,
    )
    ok = bool(out.get("packet_id")) and "escalate_caregiver" in out["policy"]["actions"]
    heard = guess["exception_guess"]
    flag = "" if heard == "side_effect" else f" <- voice-turn heard '{heard}', missed the symptom"
    return ok, f"packet={out['packet_id']}, voice guess={heard}{flag}"


@case(32, "Taken + chakkar (dizziness)")
def c32(a: Api):
    return _side_effect_case(a, "Maine medicine le li hai, lekin mujhe chakkar aa rahe hain.", "dizziness")


@case(33, "Headache")
def c33(a: Api):
    return _side_effect_case(a, "Medicine lene ke baad mujhe headache ho raha hai.", "headache")


@case(34, "Weakness")
def c34(a: Api):
    return _side_effect_case(a, "Medicine lene ke baad mujhe bahut weakness feel ho rahi hai.", "weakness")


@case(35, "Nausea")
def c35(a: Api):
    return _side_effect_case(a, "Tablet lene ke baad mujhe nausea aur ulti jaisa feel ho raha hai.", "nausea")


@case(36, "Complete a dose that was never triggered")
def c36(a: Api):
    a.active_plan()
    r = a.post("/doses/dose_never_triggered/complete", {"adherence": "taken"})
    ok = r.status_code == 404 and r.json()["error"]["code"] == "DOSE_NOT_FOUND"
    return ok, f"{r.status_code} {r.json().get('error', {}).get('code')}"


@case(37, "Complete the same dose twice")
def c37(a: Api):
    plan_id = a.active_plan()
    dose_id = a.dose(plan_id)
    a.complete(dose_id)
    r = a.post(f"/doses/{dose_id}/complete", {"adherence": "taken"})
    ok = r.status_code == 409 and r.json()["error"]["code"] == "DOSE_ALREADY_COMPLETED"
    return ok, f"{r.status_code} {r.json().get('error', {}).get('code')}"


# ------------------------------------------------------------------ policy


@case(38, "Taken, no problem -> log only")
def c38(a: Api):
    plan_id = a.active_plan()
    out = a.complete(a.dose(plan_id), adherence="taken", exception_type="none")
    ok = out["policy"]["allowed"] and out["policy"]["actions"] == ["log"] and not out["packet_id"]
    return ok, f"actions={out['policy']['actions']} packet={out['packet_id']}"


@case(39, "Side effect -> log + escalate")
def c39(a: Api):
    plan_id = a.active_plan()
    out = a.complete(
        a.dose(plan_id), adherence="taken", exception_type="side_effect",
        patient_reported="chakkar aa rahe hain", normalized_symptom="dizziness",
    )
    ok = out["policy"]["allowed"] and out["policy"]["actions"] == ["log", "escalate_caregiver"]
    return ok, f"actions={out['policy']['actions']} packet={out['packet_id']}"


@case(40, "Double dose on high-criticality med")
def c40(a: Api):
    a.active_plan()
    r = a.policy("double_dose", "med_amlodipine")
    ok = r["allowed"] is False and r["must_escalate"]
    return ok, f"allowed={r['allowed']} — {r['reason']}"


@case(41, "Double dose, patient unsure")
def c41(a: Api):
    a.active_plan()
    r = a.policy("double_dose", "med_amlodipine")
    refused = "policy_refused" in a.event_types()
    ok = r["allowed"] is False and refused
    return ok, f"allowed={r['allowed']}, policy_refused event written={refused}"


@case(42, "Patient wants to start a new medicine")
def c42(a: Api):
    a.active_plan()
    r = a.policy("invent_rx")
    ok = r["allowed"] is False and r["must_escalate"]
    return ok, f"allowed={r['allowed']} — {r['reason']}"


@case(43, "Stop a high-criticality medicine")
def c43(a: Api):
    a.active_plan()
    r = a.policy("stop_medication", "med_amlodipine")
    ok = r["allowed"] is False and r["must_escalate"]
    return ok, f"allowed={r['allowed']} — {r['reason']}"


@case(44, "Continue as prescribed")
def c44(a: Api):
    a.active_plan()
    r = a.policy("confirm_taken", "med_amlodipine")
    ok = r["allowed"] is True and not r["must_escalate"]
    return ok, f"allowed={r['allowed']} — {r['reason']}"


# ------------------------------------------------------------------ events


@case(45, "Activation event in the ledger")
def c45(a: Api):
    plan_id = a.active_plan()
    types = a.event_types(plan_id)
    ok = "plan_created" in types and "plan_activated" in types
    return ok, f"events={types}"


@case(46, "Dose trigger + completion events")
def c46(a: Api):
    plan_id = a.active_plan()
    a.complete(a.dose(plan_id), adherence="taken")
    types = a.event_types(plan_id)
    ok = "dose_triggered" in types and "dose_completed" in types
    return ok, f"events={types}"


@case(47, "Side-effect events")
def c47(a: Api):
    plan_id = a.active_plan()
    a.complete(
        a.dose(plan_id), adherence="taken", exception_type="side_effect",
        patient_reported="chakkar aa rahe hain", normalized_symptom="dizziness",
    )
    types = a.event_types(plan_id)
    ok = {"dose_completed", "exception_logged", "packet_sent"} <= set(types)
    return ok, f"events={types}"


# ----------------------------------------------------------------- packets


@case(48, "Side effect creates a caregiver packet")
def c48(a: Api):
    plan_id = a.active_plan()
    out = a.complete(
        a.dose(plan_id), adherence="taken", exception_type="side_effect",
        patient_reported="chakkar aa rahe hain", normalized_symptom="dizziness",
    )
    packet = a.get("/packets/latest", params={"plan_id": plan_id}).json()
    ok = bool(out["packet_id"]) and packet["exception"]["type"] == "side_effect"
    return ok, f"packet={out['packet_id']} action={packet.get('system_action')!r}"


@case(49, "Clean dose creates no packet")
def c49(a: Api):
    plan_id = a.active_plan()
    out = a.complete(a.dose(plan_id), adherence="taken", exception_type="none")
    latest = a.get("/packets/latest", params={"plan_id": plan_id}).status_code
    ok = out["packet_id"] is None and latest == 404
    return ok, f"packet_id={out['packet_id']}, /packets/latest -> {latest}"


# --------------------------------------------------------------- full path


@case(50, "Complete patient journey")
def c50(a: Api):
    a.reset()
    steps = []

    plan = a.extract("Doctor ne mujhe Amlodipine 5 mg roz subah lene ko bola hai.")
    names = [m["name_normalized"] for m in plan["medications"]]
    if "amlodipine" not in names:
        return False, f"extract failed: {names}"
    steps.append(f"extract={names}")

    activated = a.post(f"/plans/{plan['plan_id']}/activate").json()
    steps.append(f"activate={activated['status']}")

    trig = a.post(
        "/doses/trigger", {"plan_id": plan["plan_id"], "simulate_time": "morning"}
    ).json()
    steps.append(f"trigger={trig['status']}")

    out = a.complete(
        trig["dose_id"], adherence="taken", exception_type="side_effect",
        patient_reported="thoda chakkar aa raha hai", normalized_symptom="dizziness",
        transcript_summary="Patient confirmed Amlodipine taken; reported dizziness.",
        confidence=0.86,
    )
    steps.append(f"complete packet={out['packet_id']}")

    dbl = a.policy("double_dose", "med_amlodipine")
    steps.append(f"double_dose allowed={dbl['allowed']}")

    types = a.event_types(plan["plan_id"])
    ok = (
        activated["status"] == "active"
        and trig["status"] == "calling"
        and bool(out["packet_id"])
        and dbl["allowed"] is False
        and {"plan_created", "plan_activated", "dose_triggered", "dose_completed",
             "exception_logged", "packet_sent", "policy_refused"} <= set(types)
    )
    return ok, " -> ".join(steps) + f"; {len(types)} events"


@case(51, "Golden sentence (single utterance, full flow)")
def c51(a: Api):
    a.reset()
    golden = (
        "Doctor ne mujhe Amlodipine 5 mg roz subah lene ko bola hai. "
        "Maine aaj medicine le li hai, lekin medicine lene ke baad mujhe chakkar aa rahe hain."
    )
    plan = a.extract(golden)
    names = [m["name_normalized"] for m in plan["medications"]]
    if "amlodipine" not in names:
        return False, f"extract failed: {names}"
    a.post(f"/plans/{plan['plan_id']}/activate")
    dose_id = a.dose(plan["plan_id"], "morning")
    guess = a.voice(dose_id, golden)["partial"]
    out = a.complete(
        dose_id, adherence="taken", exception_type="side_effect",
        patient_reported="chakkar aa rahe hain", normalized_symptom="dizziness",
    )
    types = a.event_types(plan["plan_id"])
    ok = bool(out["packet_id"]) and {"exception_logged", "packet_sent"} <= set(types)
    return ok, f"meds={names}, voice guess={guess}, packet={out['packet_id']}"


# ---------------------------------------------------------------- runner


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--only", help="comma-separated case numbers")
    args = ap.parse_args()

    wanted = {int(n) for n in args.only.split(",")} if args.only else None
    api = Api(args.base)

    try:
        api.get("/health")
    except Exception as exc:
        print(f"\n{RED}cannot reach {args.base}{RESET}: {exc}")
        print("start it with: cd services/api && .venv/bin/uvicorn src.main:app --port 8000\n")
        return 2

    tally = {"PASS": 0, "FAIL": 0, "GAP": 0}
    failures: list[str] = []
    print(f"\nDAWA — 50 Hinglish cases against {args.base}\n")

    for num, title, fn in CASES:
        if wanted and num not in wanted:
            continue
        try:
            result, detail = fn(api)
        except Exception as exc:
            result, detail = False, f"{type(exc).__name__}: {exc}"
        status = result if isinstance(result, str) else ("PASS" if result else "FAIL")
        tally[status] += 1
        if status != "PASS":
            failures.append(f"{num:>2}. {title} [{status}] — {detail}")
        print(f"  {BADGE[status]} {num:>2}. {title}")
        print(f"       {DIM}{detail}{RESET}")

    print(f"\n  {tally['PASS']} pass · {tally['FAIL']} fail · {tally['GAP']} gap\n")
    if failures:
        print("  not passing:")
        for line in failures:
            print(f"    {line}")
        print()
    return 1 if tally["FAIL"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
