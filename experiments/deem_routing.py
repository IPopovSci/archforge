"""Deem-4B decision experiments on the frozen shadow suites (tracked research driver).

Compares, on the same frozen cases already measured for GLiNER and the path rules:
  A. model-alone routing on the 13-case suite,
  B. floor-first selective routing on the 14-case suite (the landed assess band),
  C. the System One typed protocol vs the naive chat-completions protocol,
  D. calibrated abstention via the published conformal threshold.
Writes experiments/results/deem-routing-results.json.
"""
import json
import statistics
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import harness as h
from scripts import shadow_decisions as shadow

PROFILES = ("FAST", "STANDARD", "FULL")
CRITERIA = {
    "FAST": "documentation correction, trivial wording or formatting, no executable code change",
    "STANDARD": "contained implementation fix inside one module, no public interface change",
    "FULL": "architecture or interface design, cross-component feature, policy change or new subsystem",
}
SYSTEMONE = "http://127.0.0.1:8020/v1/systemone"
CHAT = "http://127.0.0.1:8010/v1/chat/completions"
CONFORMAL_90 = 0.505204  # published choice threshold for 90% coverage


def post(url, payload, timeout=240):
    request = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                     headers={"Content-Type": "application/json"})
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read())
    return body, round((time.perf_counter() - started) * 1000, 1)


def state_text(request, paths):
    return (f"Software change request: \"{request}\"\n"
            f"Intended paths: {', '.join(paths)}")


def deem_typed(request, paths):
    body, ms = post(SYSTEMONE, {
        "state": state_text(request, paths),
        "questions": {"profile": {"type": "choice",
                                  "instructions": "Which review profile does this change need?",
                                  "criteria": CRITERIA}},
        "reasoning": "off", "abstain": False})
    answer = body["answers"]["profile"]
    row = dict(provider="deem-4b-q4km", protocol="systemone",
               prediction=answer["choice"], probabilities=answer["probabilities"],
               confidence=answer["confidence"], milliseconds=ms,
               tokens=body.get("usage", {}))
    # Calibrated abstention: the published conformal threshold for 90% coverage.
    row["abstained_90"] = answer["probabilities"][answer["choice"]] < CONFORMAL_90
    return row


def deem_chat(request, paths):
    prompt = (f"You are deciding how much review a software change needs.\n"
              f"Choose exactly one profile:\n"
              f"- FAST: {CRITERIA['FAST']}\n"
              f"- STANDARD: {CRITERIA['STANDARD']}\n"
              f"- FULL: {CRITERIA['FULL']}\n\n"
              f"{state_text(request, paths)}\n\n"
              f"Answer with exactly one word: FAST, STANDARD, or FULL.")
    body, ms = post(CHAT, {"messages": [{"role": "user", "content": prompt}],
                           "temperature": 0, "max_tokens": 1024})
    message = body["choices"][0]["message"]
    text = (message.get("content") or "").strip().upper()
    prediction = next((p for p in PROFILES if p in text.split()), None)
    return dict(provider="deem-4b-q4km", protocol="chat",
                prediction=prediction, milliseconds=ms,
                tokens={"input": body["usage"]["prompt_tokens"],
                        "output": body["usage"]["completion_tokens"]},
                raw_answer=text[:40], abstained_90=prediction is None)


def observed_from(mock_diff):
    if mock_diff is None:
        return None
    before, after = map(h.public_api_digest, mock_diff)
    return "FULL" if before != after else "STANDARD"


def floor_for(paths, observed):
    rule = h.profile(list(paths))
    if observed is not None and PROFILES.index(observed) > PROFILES.index(rule):
        return observed, rule
    return rule, rule


def run():
    results = {"suites": {}, "notes": {
        "systemone": SYSTEMONE, "chat": CHAT,
        "conformal_90_choice": CONFORMAL_90,
        "cpu_threads": 8, "gpu": "chat protocol only, llama.cpp b12521 Vulkan -ngl 99"}}

    # A. Model alone on the 13-case routing suite (GLiNER recorded 9/13, rules 12/13).
    rows = []
    for request, paths, expected in shadow.CASES:
        typed = deem_typed(request, paths)
        rows.append(dict(request=request, expected=expected, **typed))
    results["suites"]["routing13"] = {
        "rows": rows,
        "metrics": metrics(rows, "prediction"),
        "abstain90_metrics": selective_metrics(rows, key="prediction",
                                                abstain_field="abstained_90"),
    }

    # B. Selective floor-first on the 14-case suite (GLiNER selective recorded
    #    13/14 with 5 calls; deterministic floor alone recorded 12/14).
    results["suites"]["selective14"] = {}
    for name, consult in (("selective_deem", deem_typed), ("selective_deem_chat", deem_chat)):
        rows = []
        for request, paths, expected, mock_diff in shadow._SELECTIVE_CASES:
            paths = list(paths)
            observed = observed_from(mock_diff)
            floor, rule = floor_for(paths, observed)
            tests_only = bool(paths) and all(p.startswith("tests/") for p in paths)
            row = dict(request=request, paths=paths, expected=expected, observed=observed,
                       path_rule=rule, floor=floor, recommendation=floor, vote=None,
                       disagreement=False, called=False)
            if floor == "STANDARD" and not tests_only:
                vote = consult(request, paths)
                row.update(called=True, vote=vote["prediction"], disagreement=(
                    vote["prediction"] is not None and vote["prediction"] != floor),
                    milliseconds=vote["milliseconds"], tokens=vote.get("tokens"),
                    probabilities=vote.get("probabilities"),
                    abstained_90=vote.get("abstained_90"))
                if vote["prediction"] is not None:
                    row["recommendation"] = max(floor, vote["prediction"], key=PROFILES.index)
            rows.append(row)
        results["suites"]["selective14"][name] = {
            "rows": rows, "metrics": metrics(rows, "recommendation")}

    # C. Model alone on the 14-case suite for a like-for-like GLiNER comparison.
    rows = []
    for request, paths, expected, _mock in shadow._SELECTIVE_CASES:
        typed = deem_typed(request, list(paths))
        rows.append(dict(request=request, expected=expected, **typed))
    results["suites"]["selective14"]["deem_alone"] = {
        "rows": rows, "metrics": metrics(rows, "prediction")}

    write(results)
    summary(results)


def metrics(rows, key):
    return dict(
        correct=sum(r[key] == r["expected"] for r in rows),
        total=len(rows),
        missed_full=sum(r["expected"] == "FULL" and r[key] != "FULL" for r in rows),
        unnecessary_full=sum(r["expected"] != "FULL" and r[key] == "FULL" for r in rows),
        model_calls=sum(r.get("called", True) for r in rows),
        median_ms=statistics.median([r["milliseconds"] for r in rows if r.get("milliseconds")]),
    )


def selective_metrics(rows, key, abstain_field):
    """Correctness when every abstention falls back to the deterministic floor."""
    fallback = []
    for row in rows:
        value = row[key]
        if value is None or row.get(abstain_field):
            value = row.get("floor", "STANDARD")
        fallback.append({**row, "treatment": value})
    return metrics(fallback, "treatment")


def write(results):
    (ROOT / "experiments/results/deem-routing-results.json").write_text(
        json.dumps(results, indent=1), encoding="utf-8")


def summary(results):
    print("routing13 model-alone:", json.dumps(results["suites"]["routing13"]["metrics"]))
    print("routing13 abstain90->floor:", json.dumps(results["suites"]["routing13"]["abstain90_metrics"]))
    for name in ("selective_deem", "selective_deem_chat", "deem_alone"):
        print(name, json.dumps(results["suites"]["selective14"][name]["metrics"]))


if __name__ == "__main__":
    run()
