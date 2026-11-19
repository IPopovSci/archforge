"""FEAT-DECIDE-ADAPT-001 open-gate suite (tracked research driver).

The REQ-ADAPT-B gate needs a frozen routing suite of at least thirty real
engineering requests. Every row is evidence-bound: the recorded request is a
commit subject (or an executed benchmark task request), the intended paths are
the files that commit actually changed, and the ground-truth profile is
computed deterministically from the actual outcome:

    expected = max(path rule on the actual paths,
                   public-interface impact of the actual diff)

so the label rule is the harness's own floor logic applied to what really
happened. Rows where the outcome changed a public interface inside one module
are exactly the cases a request-time advisory could catch and the path-only
floor misses. The known blind spot stays blind: semantic-FULL work inside one
file with no interface change (a new subsystem) is labeled STANDARD by this
rule, as the recorded suites already noted; the up-front semantic review
covers it.

Treatments per row (each model consulted once, predictions reused, as the
recorded paired evaluations did):
  - path_rules (deterministic floor, request-time view: paths only)
  - floor + selective Deem typed (System One, conformal abstention -> floor)
  - floor + selective Deem chat (llama-server Vulkan GPU)
  - floor + selective GLiNER 3-way
  - floor + selective GLiNER binary gate (the cheap-gate shape)
  - model-alone rows for Deem typed, Deem chat, GLiNER 3-way and the binary
    gate, for per-transport agreement and calibration.

Writes experiments/results/adapt-suite-results.json.
"""
import json
import statistics
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness as h
from scripts import shadow_decisions as shadow
import deem_routing as deem

PIN = "c6acd0e355e2713e1f6f0c7139b1529dbb6687a0"  # frozen at this main revision
GLINER_CHECKPOINT = ROOT / ".harness/models/gliner-9d1bfb848cd16d93ee56ccbc59cd92bf0f284d90"
PROFILES = ("FAST", "STANDARD", "FULL")
CONFORMAL_90 = deem.CONFORMAL_90

GATE_LABELS = ["needs full architecture review", "no architecture review needed"]


def git(*args, check=True):
    return h.run("git", *args, cwd=str(ROOT), check=check)


def commit_rows():
    """Every non-merge ancestor of the pin with at least one changed file.

    The same subject with the same file scope appears twice when a change was
    executed on divergent branches (the decision-model integration and its
    main-side twin); keep the first execution only."""
    hashes = git("rev-list", "--no-merges", PIN).stdout.split()
    rows, seen = [], set()
    for sha in hashes:
        subject = git("log", "-1", "--format=%s", sha).stdout.strip()
        files = sorted(filter(None, git("show", "--name-only", "--format=", sha).stdout.splitlines()))
        if not files:
            continue
        key = (subject, tuple(files))
        if key in seen:
            continue
        seen.add(key)
        impact = api_impact(sha, files)
        path_rule = h.profile(files)
        expected = path_rule if impact is None else max(path_rule, impact, key=PROFILES.index)
        rows.append(dict(request=subject, paths=files, expected=expected,
                         path_rule=path_rule, observed=impact,
                         provenance={"kind": "commit", "hash": sha}))
    return rows


def api_impact(sha, files):
    """Public-interface impact of the actual commit, the recheck way."""
    for path in files:
        if not path.endswith(".py") or path.startswith("tests/"):
            continue
        sources = []
        for ref in (sha + "^", sha):
            blob = git("show", f"{ref}:{path}", check=False)
            sources.append(blob.stdout if blob.returncode == 0 else "")
        try:
            before, after = map(h.public_api_digest, sources)
        except SyntaxError:
            return "FULL"
        if before != after:
            return "FULL"
    return None


def benchmark_rows():
    data = json.loads((ROOT / "benchmarks/tasks.json").read_text(encoding="utf-8"))
    rows = []
    for task in data["tasks"]:
        files = [task["file"]] if task.get("file") else []
        rows.append(dict(request=task["request"], paths=files, expected=task["profile"],
                         path_rule=h.profile(files), observed=None,
                         provenance={"kind": "benchmark", "id": task["id"]}))
    return rows


def floor_row(row):
    """Request-time assessment: paths only, no diff evidence."""
    paths = row["paths"]
    tests_only = bool(paths) and all(p.startswith("tests/") for p in paths)
    consult = row["path_rule"] == "STANDARD" and not tests_only
    return dict(consult=consult, tests_only=tests_only, floor=row["path_rule"])


def selective(row, vote, abstained=False):
    """The landed band policy: consult, promote on the vote, never go below floor."""
    state = floor_row(row)
    if not state["consult"]:
        return state["floor"], False
    if vote is None or abstained:
        return state["floor"], False
    return max(state["floor"], vote, key=PROFILES.index), vote != state["floor"]


def metrics(rows, key):
    timings = [r["milliseconds"] for r in rows if r.get("milliseconds")]
    return dict(
        correct=sum(r[key] == r["expected"] for r in rows),
        total=len(rows),
        missed_full=sum(r["expected"] == "FULL" and r[key] != "FULL" for r in rows),
        unnecessary_full=sum(r["expected"] != "FULL" and r[key] == "FULL" for r in rows),
        model_calls=sum(r.get("consulted", False) for r in rows),
        median_ms=statistics.median(timings) if timings else None,
    )


def run():
    suite = commit_rows() + benchmark_rows()
    composition = {p: sum(r["expected"] == p for r in suite) for p in PROFILES}
    print(f"suite: {len(suite)} rows, expected composition {composition}")
    band = sum(floor_row(r)["consult"] for r in suite)
    print(f"in-band (selective consult) rows: {band}")

    results = dict(pin=PIN, rows=suite, notes={
        "label_rule": "expected = max(path rule on actual paths, public-API impact of actual diff)",
        "conformal_90_choice": CONFORMAL_90,
        "typed": deem.SYSTEMONE, "chat": deem.CHAT,
        "gliner_checkpoint": GLINER_CHECKPOINT.name})

    # Deem-4B on both transports, every row (reused by the selective treatments).
    for name, consult in (("deem_typed", deem.deem_typed), ("deem_chat", deem.deem_chat)):
        started = time.perf_counter()
        rows = []
        for case in suite:
            vote = consult(case["request"], case["paths"])
            rows.append(dict(request=case["request"], provenance=case["provenance"],
                             expected=case["expected"], prediction=vote["prediction"],
                             probabilities=vote.get("probabilities"),
                             confidence=vote.get("confidence"),
                             abstained_90=vote.get("abstained_90"),
                             raw_answer=vote.get("raw_answer"),
                             milliseconds=vote["milliseconds"], tokens=vote.get("tokens")))
        results[name] = dict(rows=rows, seconds=round(time.perf_counter() - started, 1))
        print(name, json.dumps(metrics(rows, "prediction")))

    # GLiNER: 3-way classification and the binary cheap gate.
    import os
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from gliner2 import AutoExtractor
    import torch
    torch.set_num_threads(8)
    model = AutoExtractor.from_pretrained(str(GLINER_CHECKPOINT)).to("cpu").eval()

    def gliner_call(request, labels):
        started = time.perf_counter()
        raw = model.classify_text(request, {"menu": labels})
        answer = raw.get("menu")
        ms = round((time.perf_counter() - started) * 1000, 1)
        return answer, ms

    with torch.inference_mode():
        for name, labels, key in (("gliner3", list(shadow.LABELS), "workflow"),
                                  ("gliner_gate", GATE_LABELS, "gate")):
            rows = []
            for case in suite:
                answer, ms = gliner_call(case["request"], labels)
                if name == "gliner3":
                    prediction = shadow.LABELS.get(answer)
                else:
                    prediction = "FULL" if answer == GATE_LABELS[0] else None
                rows.append(dict(request=case["request"], provenance=case["provenance"],
                                 expected=case["expected"], answer=answer,
                                 prediction=prediction, milliseconds=ms))
            results[name] = dict(rows=rows)
            print(name, json.dumps(metrics(rows, "prediction")))

    # Treatments: floor-first selective, predictions reused per row.
    def derive(treatment, votes, abstain_key=None):
        rows = []
        for case, vote in zip(suite, votes):
            abstained = bool(vote.get(abstain_key)) if abstain_key else vote["prediction"] is None
            recommendation, disagreement = selective(case, vote["prediction"], abstained)
            rows.append(dict(request=case["request"], paths=case["paths"],
                             expected=case["expected"], floor=floor_row(case)["floor"],
                             consulted=floor_row(case)["consult"], vote=vote["prediction"],
                             abstained=abstained, disagreement=disagreement,
                             milliseconds=vote.get("milliseconds") if floor_row(case)["consult"] else None,
                             recommendation=recommendation))
        return dict(rows=rows, metrics=metrics(
            [{**r, "consulted": r["consulted"]} for r in rows], "recommendation"))

    votes_typed = results["deem_typed"]["rows"]
    votes_chat = results["deem_chat"]["rows"]
    results["treatments"] = {
        "path_rules": dict(
            metrics=metrics(
                [{**c, "consulted": False} for c in suite], "path_rule")),
        "selective_deem_typed": derive("typed", votes_typed, "abstained_90"),
        "selective_deem_chat": derive("chat", votes_chat),
        "selective_gliner3": derive("gliner3", results["gliner3"]["rows"]),
        "selective_gliner_gate": derive("gate", results["gliner_gate"]["rows"]),
    }
    for name in ("path_rules", "selective_deem_typed", "selective_deem_chat",
                 "selective_gliner3", "selective_gliner_gate"):
        print(name, json.dumps(results["treatments"][name]["metrics"]))

    # Item 2: per-transport agreement and calibration.
    agree = [t["prediction"] == c["prediction"] and t["prediction"] is not None
             for t, c in zip(votes_typed, votes_chat)]
    disagreements = [dict(request=case["request"],
                          expected=case["expected"],
                          typed=t["prediction"], typed_confidence=t.get("confidence"),
                          chat=c["prediction"], chat_raw=c.get("raw_answer"))
                      for case, t, c in zip(suite, votes_typed, votes_chat)
                      if t["prediction"] != c["prediction"]]
    abstained = [t for t in votes_typed if t.get("abstained_90")]
    results["calibration"] = {
        "agreement": dict(both=sum(agree), rows=len(agree),
                          typed_none=sum(t["prediction"] is None for t in votes_typed),
                          chat_none=sum(c["prediction"] is None for c in votes_chat)),
        "disagreements": disagreements,
        "typed_abstained_90": [dict(request=a["request"], prediction=a["prediction"],
                                    confidence=a.get("confidence"),
                                    expected=a["expected"]) for a in abstained],
        "typed_correct_when_confident": dict(
            correct=sum(t["prediction"] == t["expected"] for t in votes_typed
                        if not t.get("abstained_90")),
            total=sum(not t.get("abstained_90") for t in votes_typed)),
        "typed_correct_when_abstained_floor_would_apply": [
            dict(request=a["request"], expected=a["expected"], prediction=a["prediction"],
                 confidence=a.get("confidence")) for a in abstained],
        "chat_raw_answers": sorted({(c.get("raw_answer") or "<none>") for c in votes_chat}),
    }

    # Item 4: the chat first-word parser against real answer phrasings.
    results["chat_parser"] = dict(
        parsed=sum(c["prediction"] is not None for c in votes_chat),
        unparsed=[c for c in votes_chat if c["prediction"] is None])

    (ROOT / "experiments/results/adapt-suite-results.json").write_text(
        json.dumps(results, indent=1), encoding="utf-8")
    print("written experiments/results/adapt-suite-results.json")


if __name__ == "__main__":
    run()
