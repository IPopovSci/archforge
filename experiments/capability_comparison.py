"""Capability-classification head-to-head: Deem-4B vs GLiNER2.5-Decide.

Ground truth is the committed tickets themselves: every ticket binds its
intent to real catalog components (the tach.toml module menu). Both models
see the same menu surface (module paths only).

  Top-1:   Deem choice (16-option criteria menu) vs GLiNER classify_text.
  Sets:    Deem one request with one noul question per module (parallel
           answer slots) vs GLiNER binary classify per module.
  Triage:  GLiNER re-answers the six evidence-triage cases Deem scored 6/6.

Runs under the decision-env python (gliner2 + stdlib urllib).
Writes experiments/results/capability-results.json.
"""
import json
import os
import statistics
import time
import tomllib
import urllib.request
from pathlib import Path

os.environ["HF_HUB_OFFLINE"] = "1"
os.environ["TRANSFORMERS_OFFLINE"] = "1"

ROOT = Path(__file__).resolve().parents[1]
SYSTEMONE = "http://127.0.0.1:8020/v1/systemone"


def post(payload):
    request = urllib.request.Request(SYSTEMONE, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=600) as response:
        body = json.loads(response.read())
    body["latency_ms"] = round((time.perf_counter() - started) * 1000, 1)
    return body


def menu():
    policy = tomllib.loads((ROOT / "tach.toml").read_text())
    return sorted(m["path"] for m in policy["modules"])


def tickets():
    out = []
    for path in sorted((ROOT / "tickets").glob("*.json")):
        ticket = json.loads(path.read_bytes())
        out.append((ticket["id"], ticket["intent"], set(ticket["components"])))
    return out


def deem_top1(intent, modules):
    criteria = {m: f"the task requires changes in this component ({m.replace('.', '/')}.py)"
                for m in modules}
    body = post({"state": f"Software engineering task in the Archforge architecture harness "
                           f"repository: \"{intent}\"",
                 "questions": {"component": {"type": "choice",
                                             "instructions": "Which component does this task change?",
                                             "criteria": criteria}},
                 "reasoning": "off", "abstain": False})
    answer = body["answers"]["component"]
    return dict(prediction=answer["choice"], confidence=answer["confidence"],
                latency_ms=body["latency_ms"], tokens=body.get("usage", {}))


def deem_set(intent, modules):
    questions = {m: {"type": "noul",
                     "instructions": f"This task requires changes in this component ({m.replace('.', '/')}.py)."}
                 for m in modules}
    body = post({"state": f"Software engineering task in the Archforge architecture harness "
                           f"repository: \"{intent}\"",
                 "questions": questions, "reasoning": "off", "abstain": False})
    predicted = {m for m in modules if body["answers"][m]["noul"] >= 0.5}
    scores = {m: round(body["answers"][m]["noul"], 3) for m in modules}
    return dict(prediction=sorted(predicted), scores=scores,
                latency_ms=body["latency_ms"], tokens=body.get("usage", {}))


def gliner_model():
    from gliner2 import AutoExtractor

    started = time.perf_counter()
    model = AutoExtractor.from_pretrained(
        str((ROOT / ".harness/models/gliner-9d1bfb848cd16d93ee56ccbc59cd92bf0f284d90").resolve())
    ).to("cpu").eval()
    return model, round(time.perf_counter() - started, 1)


def gliner_top1(model, intent, modules):
    started = time.perf_counter()
    out = model.classify_text(intent, {"component": modules}, include_confidence=True)
    answer = out["component"]
    return dict(prediction=answer["label"], confidence=answer.get("confidence"),
                latency_ms=round((time.perf_counter() - started) * 1000, 1))


def gliner_set(model, intent, modules):
    predicted, latencies = [], []
    for module in modules:
        started = time.perf_counter()
        out = model.classify_text(intent, {"relevance": [module, "unrelated to this task"]},
                                  include_confidence=True)
        latencies.append(round((time.perf_counter() - started) * 1000, 1))
        if out["relevance"]["label"] == module:
            predicted.append(module)
    return dict(prediction=predicted, latency_ms=round(statistics.median(latencies), 1),
                total_ms=round(sum(latencies), 1))


def triage_cases():
    run = sorted((ROOT / ".harness/runs").glob("*"), key=lambda p: p.stat().st_mtime)[-1]
    data = json.loads((ROOT / "experiments/results/evidence-triage-results.json").read_bytes())
    seam = json.loads((ROOT / ".harness/review/decide-seam-verify.json").read_text(encoding="utf-8-sig"))

    def state_text(intent, result):
        checks = {name: row["exit"] for name, row in result["checks"].items()}
        return (f"Task intent: {intent}\n"
                f"Verification result: passed={result['passed']}, checks={json.dumps(checks)}, "
                f"problems={json.dumps(result['problems'][:4])}")

    review = json.loads((run / "review.json").read_text(encoding="utf-8"))
    red = json.loads((run / "red.json").read_text(encoding="utf-8"))
    scope = json.loads((run / "scope_rejected.json").read_text(encoding="utf-8"))
    out = [("demo green", "Stacking poison effects, five-turn expiry", review, True),
           ("demo red", "Stacking poison effects, five-turn expiry", red, False),
           ("demo scope violation", "Stacking poison effects, five-turn expiry", scope, False)]
    for row in data["rows"]:
        if row["case"].startswith("seam"):
            variant = json.loads(json.dumps(seam))
            variant["problems"] = ([] if row["case"] == "seam verified" else
                                   ["REQ-SEAM-C lacks passing linked acceptance tests"]
                                   if row["case"] == "seam dropped requirement" else
                                   ["Unapproved public interface change in harness.py: a6a86032"])
            variant["passed"] = not variant["problems"]
            out.append((row["case"],
                        "Floor-first advisory decision seam with recorded assessments",
                        variant, row["satisfied"]))
    return out, state_text


def run():
    modules = menu()
    cases = tickets()
    model, gliner_load = gliner_model()
    results = {"menu_size": len(modules), "cases": len(cases), "gliner_load_s": gliner_load,
               "rows": {"deem_top1": [], "gliner_top1": [], "deem_set": [], "gliner_set": []}}

    for ticket_id, intent, truth in cases:
        for treatment, fn in (("deem_top1", lambda: deem_top1(intent, modules)),
                               ("gliner_top1", lambda: gliner_top1(model, intent, modules))):
            row = fn()
            row.update(ticket=ticket_id, truth=sorted(truth))
            row["in_set"] = row["prediction"] in truth
            results["rows"][treatment].append(row)
        for treatment, fn in (("deem_set", lambda: deem_set(intent, modules)),
                             ("gliner_set", lambda: gliner_set(model, intent, modules))):
            row = fn()
            predicted = set(row["prediction"])
            row.update(ticket=ticket_id, truth=sorted(truth),
                       exact=predicted == truth,
                       precision=round(len(predicted & truth) / len(predicted), 2) if predicted else None,
                       recall=round(len(predicted & truth) / len(truth), 2))
            results["rows"][treatment].append(row)

    for treatment in ("deem_top1", "gliner_top1"):
        rows = results["rows"][treatment]
        results[treatment] = dict(in_set=sum(r["in_set"] for r in rows), total=len(rows),
                                  median_ms=statistics.median([r["latency_ms"] for r in rows]))
    for treatment in ("deem_set", "gliner_set"):
        rows = results["rows"][treatment]
        results[treatment] = dict(exact=sum(r["exact"] for r in rows),
                                  mean_precision=round(statistics.mean(
                                      [r["precision"] for r in rows if r["precision"] is not None]), 2),
                                  mean_recall=round(statistics.mean([r["recall"] for r in rows]), 2),
                                  median_ms=statistics.median([r["latency_ms"] for r in rows]))

    cases, state_text = triage_cases()
    triage = []
    for name, intent, evidence, satisfied in cases:
        row = gliner_top1.__wrapped__ if False else None
        started = time.perf_counter()
        out = model.classify_text(state_text(intent, evidence),
                                  {"verdict": ["satisfied", "unsatisfied"]}, include_confidence=True)
        answer = out["verdict"]
        triage.append(dict(case=name, satisfied=satisfied, prediction=answer["label"],
                           confidence=answer.get("confidence"),
                           correct=(answer["label"] == "satisfied") == satisfied,
                           latency_ms=round((time.perf_counter() - started) * 1000, 1)))
    results["gliner_triage"] = dict(rows=triage, correct=sum(r["correct"] for r in triage),
                                    total=len(triage))

    (ROOT / "experiments/results/capability-results.json").write_text(json.dumps(results, indent=1),
                                                           encoding="utf-8")
    print(json.dumps({k: v for k, v in results.items()
                      if k in ("deem_top1", "gliner_top1", "deem_set", "gliner_set",
                               "gliner_triage")}, indent=1))


if __name__ == "__main__":
    run()
