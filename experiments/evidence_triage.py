"""Evidence-triage probe: can Deem-4B judge verified evidence against intent?

Each frozen case is real harness verification output (demo replay artifacts from
.harness/runs plus tonight's seam verification, with two structurally-real
failure variants). One request carries all three System One question shapes.
Ground truth is known per case. Writes experiments/results/evidence-triage-results.json.
"""
import json
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYSTEMONE = "http://127.0.0.1:8020/v1/systemone"

SEAM_VERIFY = json.loads(Path(
    ".harness/review/decide-seam-verify.json").read_text(encoding="utf-8")) \
    if (ROOT / ".harness/review/decide-seam-verify.json").exists() else None


def post(payload):
    request = urllib.request.Request(SYSTEMONE, data=json.dumps(payload).encode(),
                                      headers={"Content-Type": "application/json"})
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=240) as response:
        body = json.loads(response.read())
    body["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
    return body


def load_run(name):
    folder = sorted((ROOT / ".harness/runs").glob("*"), key=lambda p: p.stat().st_mtime)[-1]
    return json.loads((folder / (name + ".json")).read_text(encoding="utf-8"))


def state_text(intent, result):
    checks = {name: row["exit"] for name, row in result["checks"].items()}
    return (f"Task intent: {intent}\n"
            f"Verification result: passed={result['passed']}, checks={json.dumps(checks)}, "
            f"problems={json.dumps(result['problems'][:4])}")


def cases():
    out = []
    review = load_run("review")
    out.append(("demo green", "Stacking poison effects, five-turn expiry",
                review, True))
    red = load_run("red")
    out.append(("demo red", "Stacking poison effects, five-turn expiry", red, False))
    scope = load_run("scope_rejected")
    out.append(("demo scope violation", "Stacking poison effects, five-turn expiry",
                scope, False))
    if SEAM_VERIFY:
        out.append(("seam verified", "Floor-first advisory decision seam with recorded assessments",
                    SEAM_VERIFY, True))
        dropped = json.loads(json.dumps(SEAM_VERIFY))
        dropped["problems"] = ["REQ-SEAM-C lacks passing linked acceptance tests"]
        dropped["passed"] = False
        out.append(("seam dropped requirement", "Floor-first advisory decision seam with recorded assessments",
                    dropped, False))
        drifted = json.loads(json.dumps(SEAM_VERIFY))
        drifted["problems"] = ["Unapproved public interface change in harness.py: a6a86032"]
        drifted["passed"] = False
        out.append(("seam unapproved interface", "Floor-first advisory decision seam with recorded assessments",
                    drifted, False))
    return out


def run():
    rows = []
    for name, intent, result, satisfied in cases():
        response = post({
            "state": state_text(intent, result),
            "questions": {
                "verdict": {"type": "choice",
                            "instructions": "Does the verification evidence satisfy the intent?",
                            "criteria": {"satisfied": "checks pass, no problems, requirements linked",
                                         "unsatisfied": "failing checks, unmet requirements, scope or interface problems"}},
                "coverage": {"type": "score",
                             "instructions": "How thoroughly does the evidence cover the intent?",
                             "criteria": ["insufficient", "partial", "sufficient"]},
                "proves": {"type": "noul",
                           "instructions": "The verification evidence proves the implementation satisfies the intent."},
            },
            "reasoning": "off", "abstain": False})
        answers = response["answers"]
        rows.append(dict(
            case=name, satisfied=satisfied,
            choice=answers["verdict"]["choice"],
            choice_probabilities=answers["verdict"]["probabilities"],
            score=answers["coverage"]["score"],
            score_levels=answers["coverage"].get("levels"),
            noul=answers["proves"]["noul"],
            latency_ms=response["latency_ms"], tokens=response.get("usage", {})))
        print(name, rows[-1]["choice"], round(rows[-1]["noul"], 2),
              round(rows[-1]["score"], 2), "expected", satisfied)

    correct = sum((row["choice"] == "satisfied") == row["satisfied"] for row in rows)
    result = dict(rows=rows, correct_choice=correct, total=len(rows),
                  notes={"protocol": "systemone multi-question (choice+score+noul per request)"})
    (ROOT / "experiments/results/evidence-triage-results.json").write_text(
        json.dumps(result, indent=1), encoding="utf-8")
    print(f"choice correct: {correct}/{len(rows)}")


if __name__ == "__main__":
    run()
