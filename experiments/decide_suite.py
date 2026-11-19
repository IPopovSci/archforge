"""Deem-4B activation-suite experiment on real engineering requests (untracked research driver).

Freezes 54 real work items from this repository's own history: each case is the
actual request (commit subject phrased as a request), the actual changed paths,
and the hand-labeled workflow the work genuinely required. Observed interface
impact is computed from the real commit diff, not mocked. Treatments:
  A. path rules alone,
  B. rules + observed impact (the landed floor),
  C. GLiNER alone (recorded baseline treatment),
  D. Deem typed alone, E. Deem chat alone,
  F. floor + selective Deem typed, G. floor + selective Deem chat (the landed band),
including typed calibrated abstentions and typed/chat agreement.
Writes experiments/results/decide-suite-results.json.
"""
import json
import os
import statistics
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import harness as h

PROFILES = ("FAST", "STANDARD", "FULL")
CRITERIA = {
    "FAST": "documentation correction, trivial wording or formatting, no executable code change",
    "STANDARD": "contained implementation fix inside one module, no public interface change",
    "FULL": "architecture or interface design, cross-component feature, policy change or new subsystem",
}
LABELS = {"documentation correction": "FAST", "contained implementation fix": "STANDARD",
          "architecture or interface design": "FULL"}
SYSTEMONE = "http://127.0.0.1:8020/v1/systemone"
CHAT = "http://127.0.0.1:8010/v1/chat/completions"
CONFORMAL_90 = 0.505204
GLINER = ROOT / ".harness/models/gliner-9d1bfb848cd16d93ee56ccbc59cd92bf0f284d90"

# (commit, request, actual changed paths, hand-labeled required workflow)
SUITE = [
    ("cf6cd70", "Document Codex setup, the verified fixture and the remaining readiness gates.",
     ("README.md", "docs/usage/checklist.md", "docs/usage/research-results.md"), "FAST"),
    ("6ecb710", "Record the self-hosting workflow and the measured local routing results.",
     ("README.md", "docs/usage/checklist.md", "docs/usage/research-results.md"), "FAST"),
    ("228066d", "Record the paired routing evidence and the validated role workflows.",
     ("docs/usage/checklist.md", "docs/usage/research-results.md"), "FAST"),
    ("15417ec", "Document the staged semantic lookup and the actual Windows setup findings.",
     ("README.md", "docs/usage/checklist.md", "docs/usage/research-results.md"), "FAST"),
    ("421d792", "Record the mature-project validation results in the Godot docs.",
     ("docs/usage/godot.md",), "FAST"),
    ("7792933", "Prepare the Trail GDScript patch notes for upstream filing.",
     ("docs/usage/trail-gdscript-upstream.md",), "FAST"),
    ("946c2c5", "Record agent-harness loop-guard observations and the design.",
     ("docs/usage/agent-loop-guard.md",), "FAST"),
    ("ed505b3", "Record the loop-guard scope decision.",
     ("docs/usage/agent-loop-guard.md",), "FAST"),
    ("ba4bbcb", "Rewrite the README as a plain-language project overview.",
     ("README.md",), "FAST"),
    ("e6dc728", "Record the wired Deem adapter, both transports and the first live consults.",
     ("docs/usage/research-results.md",), "FAST"),
    ("989472b", "Explain the underlying tools in the README: Tach, Trail, pytest, Pydantic, MCP.",
     ("README.md",), "FAST"),
    ("b4551d6", "Constrain each live role with its output schema.",
     ("scripts/live_fixture.py",), "STANDARD"),
    ("bd5d15a", "Specify selective decision routing acceptance cases.",
     ("tests/test_blend_001.py",), "STANDARD"),
    ("63c62d5", "Freeze the embedding experiment acceptance checks.",
     ("tests/test_eval_002.py",), "STANDARD"),
    ("bfebaab", "Record the complete ten-task Codex benchmark.",
     ("benchmarks/tasks.json", "docs/usage/checklist.md", "docs/usage/research-results.md"), "STANDARD"),
    ("e69af21", "Register the GDScript integration ticket and the parked backlog.",
     ("tickets/BENCH-OPENCODE-001.json", "tickets/FEAT-DAG-001.json",
      "tickets/FEAT-DECIDE-LOCAL-001.json", "tickets/FEAT-GDSCRIPT-001.json"), "STANDARD"),
    ("0646879", "Register the Godot hygiene ticket.",
     ("tickets/FEAT-GODOT-HYGIENE-001.json",), "STANDARD"),
    ("2ceee91", "Register the documentation layer ticket.",
     ("tickets/FEAT-DOC-LAYER-001.json",), "STANDARD"),
    ("6562863", "Register the agent external-communication rules ticket.",
     ("tickets/FEAT-AGENT-RULES-001.json",), "STANDARD"),
    ("40a3bfc", "Register the verify check generalization ticket.",
     ("tickets/FEAT-VERIFY-CHECKS-001.json",), "STANDARD"),
    ("c72e75c", "Register the development-order policy ticket.",
     ("tickets/FEAT-PHASES-001.json",), "STANDARD"),
    ("255b99d", "Register the Archforge naming ticket.",
     ("tickets/FEAT-NAMING-001.json",), "STANDARD"),
    ("af5820e", "Register the decision seam ticket.",
     ("tickets/FEAT-DECIDE-SEAM-001.json",), "STANDARD"),
    ("8142865", "Register the role-fence tolerance ticket and bind the MCP launcher to the project venv.",
     ("opencode.json", "tickets/FEAT-ROLE-FENCE-001.json"), "STANDARD"),
    ("e24e101", "Record the Deem-4B decision experiments and register the adapter gate.",
     ("docs/usage/catalog.md", "docs/usage/research-results.md",
      "tickets/FEAT-DECIDE-ADAPT-001.json"), "STANDARD"),
    ("bbb716e", "Record the capability head-to-head and revise GLiNER's placement.",
     ("docs/usage/catalog.md", "docs/usage/research-results.md",
      "tickets/FEAT-DECIDE-ADAPT-001.json"), "STANDARD"),
    ("f2c29dd", "Track the README presentation test to the plain-language rewrite.",
     ("tests/test_feat_naming_001.py",), "STANDARD"),
    ("d7ecdc1", "Resolve the adapter transport unknowns on the decision ticket.",
     ("tickets/FEAT-DECIDE-ADAPT-001.json",), "STANDARD"),
    ("173f089", "Close FEAT-DECIDE-LOCAL-001 on the recorded Deem-4B evidence.",
     ("docs/usage/catalog.md", "tests/test_feat_decide_local_001.py"), "STANDARD"),
    ("ed2753d", "Register the linter tickets from the parallel session.",
     ("docs/usage/catalog.md", "tickets/LINT-GD-1.json", "tickets/LINT-PY-1.json"), "STANDARD"),
    ("63a8626", "Bootstrap the host-neutral harness with the compiler, server and baseline fixture.",
     ("harness.py", "server.py", "fixture/entities.py", "fixture/combat.py",
      "fixture/turn_lifecycle.py"), "FULL"),
    ("42873da", "Exercise subscription model roles against the compiled fixture.",
     ("scripts/live_fixture.py", "server.py"), "FULL"),
    ("ba79dc3", "Index and verify harness modules and bind architecture changes to reviewed contracts.",
     ("harness.py", "scripts/shadow_decisions.py", "tach.toml", "tests/test_self_001.py"), "FULL"),
    ("c92f9e2", "Enforce fresh fixed-model Codex roles and retain thread receipts.",
     ("AGENTS.md", "README.md", "scripts/codex_role.py", "scripts/live_fixture.py",
      "tach.toml", "tests/test_role_001.py"), "FULL"),
    ("6873e64", "Verify scoped Sol edits independently of unattended shell availability.",
     ("README.md", "scripts/codex_role.py", "tests/test_edit_001.py"), "FULL"),
    ("e9d10ca", "Protect ordinary exported bindings in the shared public interface check.",
     ("harness.py", "tests/test_edit_001.py"), "FULL"),
    ("ac66ea8", "Compare selective local inference with deterministic routing evidence.",
     ("scripts/shadow_decisions.py",), "FULL"),
    ("083f00c", "Evaluate offline embedding and lexical baselines and expose bounded semantic lookup.",
     ("scripts/shadow_decisions.py", "tests/test_eval_002.py"), "FULL"),
    ("eee677a", "Hand off revision-bound Trail records to offline MiniLM and reuse source vectors.",
     ("scripts/shadow_decisions.py", "tests/test_eval_002.py"), "FULL"),
    ("71efb73", "Share architecture roles and verification across native clients.",
     ("AGENTS.md", "README.md", "opencode.json", "scripts/codex_project.py",
      "scripts/codex_role.py", "scripts/opencode_project.py", "scripts/roles.py",
      "tach.toml", "tests/test_host_001.py", "tests/test_role_001.py"), "FULL"),
    ("69d2d3b", "Validate completed native steps and discover installed client adapters.",
     ("opencode.json", "scripts/opencode_project.py", "tests/test_host_001.py"), "FULL"),
    ("938fb09", "Set up Docker, SIGIL and the paired benchmark workflows.",
     ("README.md", "benchmarks/tasks.json", "docs/usage/checklist.md",
      "docs/usage/research-results.md", "scripts/activate.ps1", "scripts/benchmark.py",
      "scripts/sigil.cmd", "scripts/sigil.ps1", "tests/test_benchmark.py"), "FULL"),
    ("a45782c", "Register the benchmark module in architecture policy.",
     ("tach.toml",), "FULL"),
    ("1456cf1", "Index GDScript in Trail and enforce Godot boundaries.",
     ("docs/usage/godot.md", "fixture/godot/data.gd", "fixture/godot/godot.toml",
      "fixture/godot/stats.gd", "fixture/godot/ui_bad.gd", "package.json",
      "patches/trail/gdscript.scm", "scripts/godot_boundaries.py", "scripts/godot_check.py",
      "scripts/patch_trail.mjs", "tach.toml", "tests/test_feat_gdscript_001.py"), "FULL"),
    ("ca8ab2d", "Enforce Godot autoload allowlists and path hygiene.",
     ("docs/usage/godot.md", "fixture/godot/data.gd", "fixture/godot/godot.toml",
      "fixture/godot/project.godot", "fixture/godot/ui_bad.gd", "scripts/godot_boundaries.py",
      "tests/test_feat_godot_hygiene_001.py"), "FULL"),
    ("927f169", "Generate and gate the observed documentation layer.",
     ("README.md", "docs/documentation-charter.md", "docs/usage/catalog.md",
      "docs/usage/godot.md", "docs/usage/trail-gdscript-upstream.md", "scripts/doc_catalog.py",
      "tach.toml", "tests/test_feat_doc_layer_001.py"), "FULL"),
    ("667bbcd", "Require advance approval for public posting.",
     ("AGENTS.md", "docs/usage/catalog.md", "docs/usage/trail-gdscript-upstream.md",
      "tests/test_feat_agent_rules_001.py"), "FULL"),
    ("f2dca60", "Strengthen the public-posting confirmation protocol.",
     ("AGENTS.md", "docs/usage/trail-gdscript-upstream.md", "tests/test_feat_agent_rules_001.py"), "FULL"),
    ("be9f596", "Generalize contract checks into a named registry.",
     ("README.md", "docs/documentation-charter.md", "docs/usage/catalog.md", "harness.py",
      "scripts/doc_catalog.py", "tests/test_feat_verify_checks_001.py", "tests/test_self_001.py"), "FULL"),
    ("8b9d5cd", "Record development order and the fundamentals-first policy.",
     ("AGENTS.md", "docs/usage/catalog.md", "tests/test_feat_phases_001.py"), "FULL"),
    ("06f03e2", "Record the frozen check-list boundary at the compiler.",
     ("harness.py",), "FULL"),
    ("534d419", "Name the harness Archforge.",
     ("AGENTS.md", "README.md", "docs/usage/catalog.md", "tests/test_feat_naming_001.py"), "FULL"),
    ("4293331", "Land the advisory decision seam.",
     ("AGENTS.md", "README.md", "docs/usage/catalog.md", "harness.py",
      "tests/test_feat_decide_seam_001.py"), "FULL"),
    ("d21d5ab", "Land the Deem-4B advisory adapter behind the decision seam.",
     ("docs/usage/catalog.md", "scripts/shadow_decisions.py",
      "tests/test_feat_decide_adapt_001.py"), "FULL"),
]


def git_show(ref, path):
    result = subprocess.run(["git", "show", f"{ref}:{path}"], cwd=ROOT, capture_output=True,
                            encoding="utf-8", errors="replace")
    return result.stdout if result.returncode == 0 else ""


def observed_from(commit, paths):
    parent = commit + "^"
    for path in paths:
        if not path.endswith(".py") or path.startswith("tests/"):
            continue
        before, after = git_show(parent, path), git_show(commit, path)
        try:
            if h.public_api_digest(before) != h.public_api_digest(after):
                return "FULL"
        except SyntaxError:
            return "FULL"
    return None


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
    probabilities = answer.get("probabilities") or {}
    choice = answer.get("choice")
    row = dict(protocol="systemone", prediction=choice, milliseconds=ms,
               probabilities=probabilities, confidence=answer.get("confidence"))
    row["abstained_90"] = probabilities.get(choice, 0.0) < CONFORMAL_90 if choice else True
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
    text = (body["choices"][0]["message"].get("content") or "").strip().upper()
    row = dict(protocol="chat", milliseconds=ms, raw_answer=text[:40])
    row["prediction"] = next((p for p in PROFILES if p in text.split()), None)
    return row


def gliner_predict(request, classify):
    raw = classify(request, {"workflow": list(LABELS)})
    return LABELS.get(raw.get("workflow"))


def selective(request, paths, floor, tests_only, consult):
    row = dict(recommendation=floor, called=False, vote=None, abstained=False, milliseconds=None)
    if floor != "STANDARD" or tests_only:
        return row
    vote = consult(request, paths)
    row.update(called=True, vote=vote["prediction"], milliseconds=vote["milliseconds"])
    if vote["prediction"] is None or vote.get("abstained_90"):
        row.update(abstained=True)
        return row
    row["recommendation"] = max(floor, vote["prediction"], key=PROFILES.index)
    return row


def metrics(rows, key):
    return dict(
        correct=sum(r[key] == r["expected"] for r in rows), total=len(rows),
        missed_full=sum(r["expected"] == "FULL" and r[key] != "FULL" for r in rows),
        unnecessary_full=sum(r["expected"] != "FULL" and r[key] == "FULL" for r in rows),
    )


def main():
    model_calls = 0
    rows = []
    classify = None
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    from gliner2 import AutoExtractor
    import torch
    torch.set_num_threads(4)
    classify = AutoExtractor.from_pretrained(str(GLINER)).to("cpu").eval().classify_text
    started = time.perf_counter()
    with torch.inference_mode():
        for commit, request, paths, expected in SUITE:
            paths = list(paths)
            observed = observed_from(commit, paths)
            rule = h.profile(paths)
            floor = max(rule, observed, key=PROFILES.index) if observed is not None else rule
            tests_only = bool(paths) and all(p.startswith("tests/") for p in paths)
            typed = deem_typed(request, paths)
            chat = deem_chat(request, paths)
            gliner = gliner_predict(request, classify)
            model_calls += 3
            row = dict(commit=commit, request=request, paths=paths, expected=expected,
                       observed=observed, path_rules=rule, floor=floor,
                       gliner=gliner, deem_typed=typed["prediction"],
                       deem_typed_confidence=typed.get("confidence"),
                       deem_typed_probabilities=typed["probabilities"],
                       deem_typed_abstained_90=typed["abstained_90"],
                       deem_chat=chat["prediction"], deem_chat_raw=chat["raw_answer"],
                       typed_ms=typed["milliseconds"], chat_ms=chat["milliseconds"])
            row["selective_typed"] = selective(request, paths, floor, tests_only,
                                               lambda r, p: deem_typed(r, p))
            row["selective_chat"] = selective(request, paths, floor, tests_only,
                                              lambda r, p: deem_chat(r, p))
            model_calls += row["selective_typed"]["called"] + row["selective_chat"]["called"]
            rows.append(row)
    load_seconds = time.perf_counter() - started

    results = {"notes": {"suite": "54 real work items from repository history, hand-labeled",
                        "systemone": SYSTEMONE, "chat": CHAT,
                        "conformal_90_choice": CONFORMAL_90,
                        "gliner_checkpoint": GLINER.name, "model_calls": model_calls,
                        "wall_seconds": round(load_seconds, 1)}, "rows": rows}
    treatment_metrics = {
        "path_rules": metrics(rows, "path_rules"),
        "floor": metrics(rows, "floor"),
        "gliner": metrics(rows, "gliner"),
        "deem_typed": metrics(rows, "deem_typed"),
        "deem_chat": metrics(rows, "deem_chat"),
        "floor_selective_deem_typed": metrics(
            [dict(r, treatment=r["selective_typed"]["recommendation"]) for r in rows], "treatment"),
        "floor_selective_deem_chat": metrics(
            [dict(r, treatment=r["selective_chat"]["recommendation"]) for r in rows], "treatment"),
    }
    treatment_metrics["floor_selective_deem_typed"]["model_calls"] = \
        sum(r["selective_typed"]["called"] for r in rows)
    treatment_metrics["floor_selective_deem_chat"]["model_calls"] = \
        sum(r["selective_chat"]["called"] for r in rows)
    treatment_metrics["floor_selective_deem_typed"]["abstentions"] = \
        sum(r["selective_typed"]["abstained"] for r in rows)
    results["metrics"] = treatment_metrics
    (ROOT / "experiments/results/decide-suite-results.json").write_text(
        json.dumps(results, indent=1), encoding="utf-8")
    band = [r for r in rows if r["floor"] == "STANDARD" and not
            all(p.startswith("tests/") for p in r["paths"])]
    results["band"] = dict(
        ambiguous_standard_cases=len(band),
        typed_chat_agreement=sum(r["deem_typed"] == r["deem_chat"] for r in band),
        typed_median_confidence=statistics.median(
            [r["deem_typed_confidence"] for r in band if r["deem_typed_confidence"] is not None]),
        typed_below_conformal=sum(r["deem_typed_abstained_90"] for r in rows),
        typed_confidence_min=min(
            (r["deem_typed_confidence"] for r in rows if r["deem_typed_confidence"] is not None),
            default=None),
        typed_median_ms=statistics.median([r["typed_ms"] for r in rows]),
        chat_median_ms=statistics.median([r["chat_ms"] for r in rows]),
    )
    (ROOT / "experiments/results/decide-suite-results.json").write_text(
        json.dumps(results, indent=1), encoding="utf-8")
    print(json.dumps({"metrics": treatment_metrics, "band": results["band"]}, indent=1))


if __name__ == "__main__":
    main()
