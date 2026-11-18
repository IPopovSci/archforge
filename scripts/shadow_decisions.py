"""Offline CPU experiment. Predictions are advisory and never execute a routing action."""
import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path
from collections.abc import Mapping as _Mapping

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import RuleProvider
from harness import diff_paths as _diff_paths
from harness import public_api_digest as _public_api_digest, recheck as _recheck

LABELS = {"documentation correction": "FAST", "contained implementation fix": "STANDARD",
          "architecture or interface design": "FULL"}
CASES = [
    ("Correct a spelling error in the readme.", ["README.md"], "FAST"),
    ("Fix the punctuation in the setup guide.", ["docs/usage/checklist.md"], "FAST"),
    ("Clarify the example command in the usage instructions.", ["docs/usage/checklist.md"], "FAST"),
    ("Fix a broken Markdown link in the readme.", ["README.md"], "FAST"),
    ("Fix an off-by-one in the poison timer.", ["fixture/turn_lifecycle.py"], "STANDARD"),
    ("Repair the stack calculation inside the existing combat function.", ["fixture/combat.py"], "STANDARD"),
    ("Add a regression assertion for the unchanged public stacking behavior.", ["tests/test_regression.py"], "STANDARD"),
    ("Correct arithmetic in one turn without changing its interface.", ["fixture/turn_lifecycle.py"], "STANDARD"),
    ("Add a new subsystem and define its dependency rules.", ["tach.toml"], "FULL"),
    ("Change the public schema used by the compiler and its MCP adapter.", ["harness.py","server.py"], "FULL"),
    ("Change what agents are authorized to edit.", ["AGENTS.md"], "FULL"),
    ("Revise the locked replay contract in the game design bible.", ["project_example/lines-master-design-bible.md"], "FULL"),
    ("Change the required arguments of the public combat API.", ["fixture/combat.py"], "FULL"),
]

_PROFILES = ("FAST", "STANDARD", "FULL")

# Each entry specifies the expected workflow and, where applicable, a mock diff.
_SELECTIVE_CASES = (
    ("Update the README heading for the offline routing example.",
     ("README.md",), "FAST", None),
    ("Clarify where to launch the CLI in the usage checklist.",
     ("docs/usage/checklist.md",), "FAST", None),
    ("Add a regression test for a rejected revision in the evidence report.",
     ("tests/test_regression.py",), "STANDARD", None),
    ("Add assertions for the existing routing and compiler error messages.",
     ("tests/test_routing.py", "tests/test_compiler.py"), "STANDARD", None),
    ("Fix extra whitespace in the compiled contract output.",
     ("harness.py",), "STANDARD", None),
    ("Limit a combat score to its permitted range.",
     ("fixture/combat.py",), "STANDARD",
     ("def score(value): return value", "def score(value): return max(0, value)")),
    ("Fix the MCP adapter to preserve false values in evidence results.",
     ("server.py",), "STANDARD", None),
    ("Define a new plugin lifecycle inside the harness runner.",
     ("harness.py",), "FULL", None),
    ("Design a versioned report format for the MCP adapter's consumers.",
     ("server.py",), "FULL", None),
    ("Require a revision when compiling an intent into a contract.",
     ("harness.py",), "FULL",
     ("def compile_intent(intent): return intent",
      "def compile_intent(intent, revision): return intent, revision")),
    ("Return a structured turn result through the public turn lifecycle API.",
     ("fixture/turn_lifecycle.py",), "FULL",
     ("def advance(turn) -> int: return turn + 1",
      "def advance(turn) -> dict: return {'turn': turn + 1}")),
    ("Move evidence ownership from the CLI harness to the MCP adapter.",
     ("harness.py", "server.py"), "FULL", None),
    ("Allow the compiler to import the transport layer by changing the dependency policy.",
     ("tach.toml",), "FULL", None),
    ("Change which task profiles require human approval in the agent policy.",
     ("AGENTS.md",), "FULL", None),
)


def compare(classify, cases=CASES):
    rows = []
    for request, paths, expected in cases:
        enforced = RuleProvider().decide(paths, list(LABELS.values()))["choice"]
        start = time.perf_counter()
        raw = classify(request, {"workflow": list(LABELS)})
        prediction = LABELS.get(raw.get("workflow"))
        rows.append(dict(request=request, paths=paths, expected=expected, enforced=enforced,
                         prediction=prediction, milliseconds=round((time.perf_counter()-start)*1000, 1)))
    return rows


def _predict(request, classify):
    if classify is None:
        return None, "model_unavailable"
    try:
        raw = classify(request, {"workflow": list(LABELS)})
        workflow = raw.get("workflow") if isinstance(raw, _Mapping) else None
        prediction = LABELS.get(workflow) if isinstance(workflow, str) else None
    except Exception as exc:
        return None, f"classifier_failed ({type(exc).__name__})"
    if prediction is None:
        return None, "invalid_response"
    return prediction, None


def _apply_prediction(row, prediction, reason):
    row.update(
        model_called=True,
        model_prediction=prediction,
        abstained=prediction is None,
        abstention_reason=reason,
        disagreement=prediction is not None and prediction != row["floor"],
    )
    if prediction is not None:
        row["recommendation"] = max(row["floor"], prediction, key=_PROFILES.index)


def _assess(request, paths, observed, classify):
    paths = list(paths)
    path_rule = RuleProvider().decide(paths, list(_PROFILES))["choice"]
    floor = max(path_rule, observed, key=_PROFILES.index) if observed is not None else path_rule
    tests_only = bool(paths) and all(path.startswith("tests/") for path in paths)
    row = dict(
        request=request, paths=paths, path_rule=path_rule, observed=observed,
        floor=floor, recommendation=floor, model_prediction=None, model_called=False,
        abstained=False, abstention_reason=None, disagreement=False,
    )
    if floor != "STANDARD" or tests_only:
        return row
    if classify is None:
        row.update(abstained=True, abstention_reason="model_unavailable")
    else:
        _apply_prediction(row, *_predict(request, classify))
    return row


def _benchmark(classify):
    rows = []
    for request, paths, expected, mock_diff in _SELECTIVE_CASES:
        observed = None
        if mock_diff is not None:
            before, after = map(_public_api_digest, mock_diff)
            observed = "FULL" if before != after else "STANDARD"

        assessment = _assess(request, paths, observed, None)
        prediction, reason = _predict(request, classify)
        if assessment["abstained"] and classify is not None:
            _apply_prediction(assessment, prediction, reason)
        rows.append(dict(
            request=request, paths=assessment["paths"], expected=expected, observed=observed,
            path_rules=assessment["path_rule"], deterministic=assessment["floor"],
            model_only=prediction, selective=assessment["recommendation"],
            model_only_called=classify is not None, model_only_abstention_reason=reason,
            selective_called=assessment["model_called"],
            selective_abstained=assessment["abstained"],
            selective_abstention_reason=assessment["abstention_reason"],
            selective_disagreement=assessment["disagreement"],
        ))

    metrics = {}
    for treatment in ("path_rules", "deterministic", "model_only", "selective"):
        metrics[treatment] = dict(
            correct=sum(row[treatment] == row["expected"] for row in rows),
            total=len(rows),
            missed_full=sum(row["expected"] == "FULL" and row[treatment] != "FULL" for row in rows),
            unnecessary_full=sum(row["expected"] != "FULL" and row[treatment] == "FULL" for row in rows),
            per_profile={
                profile: dict(
                    correct=sum(row[treatment] == profile == row["expected"] for row in rows),
                    total=sum(row["expected"] == profile for row in rows),
                )
                for profile in _PROFILES
            },
            abstentions=sum(
                row[treatment] is None or (treatment == "selective" and row["selective_abstained"])
                for row in rows
            ),
            model_calls=sum(row.get(f"{treatment}_called", False) for row in rows),
        )
    return dict(rows=rows, metrics=metrics)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_directory", nargs="?", type=Path, help="Local model checkpoint")
    parser.add_argument("--threads", type=int, default=4, help="CPU thread count")
    parser.add_argument("--request", help="Assess one engineering request")
    parser.add_argument("--paths", nargs="+", help="Intended repository-relative paths")
    parser.add_argument("--base", help="Recheck the diff against this Git revision")
    parser.add_argument("--benchmark-selective", action="store_true", help="Run the selective benchmark")
    args = parser.parse_args()
    if args.threads < 1:
        parser.error("Expected a positive CPU thread count")
    if (args.request is None) != (args.paths is None):
        parser.error("Supply --request and --paths together")
    if args.base is not None and args.request is None:
        parser.error("--base requires --request and --paths")
    if args.benchmark_selective and args.request is not None:
        parser.error("--benchmark-selective cannot be combined with --request")

    def load_model():
        os.environ["HF_HUB_OFFLINE"] = "1"
        os.environ["TRANSFORMERS_OFFLINE"] = "1"
        from gliner2 import AutoExtractor
        import torch

        torch.set_num_threads(args.threads)
        start = time.perf_counter()
        model = AutoExtractor.from_pretrained(str(args.model_directory.resolve())).to("cpu").eval()
        return model.classify_text, torch.inference_mode, time.perf_counter() - start

    if args.request is not None:
        try:
            changed = _diff_paths(args.base) if args.base is not None else []
            observed = _recheck(args.base)["choice"] if changed else None
        except (OSError, ValueError) as exc:
            parser.error(str(exc))

        row = _assess(args.request, sorted(set(args.paths) | set(changed)), observed, None)
        load_seconds = None
        if row["abstained"] and args.model_directory is not None:
            try:
                if not args.model_directory.is_dir():
                    raise FileNotFoundError(args.model_directory)
                classify, inference_mode, load_seconds = load_model()
            except Exception as exc:
                row["abstention_reason"] = f"model_unavailable ({type(exc).__name__})"
            else:
                with inference_mode():
                    _apply_prediction(row, *_predict(args.request, classify))
        print(json.dumps(dict(
            checkpoint=args.model_directory.name if args.model_directory is not None else None,
            load_seconds=round(load_seconds, 2) if load_seconds is not None else None,
            **row,
        ), indent=2))
        return

    if args.model_directory is None or not args.model_directory.is_dir():
        parser.error("Expected a local checkpoint directory")
    classify, inference_mode, load_seconds = load_model()
    if args.benchmark_selective:
        with inference_mode():
            result = _benchmark(classify)
        print(json.dumps(dict(
            checkpoint=args.model_directory.name, device="cpu", threads=args.threads,
            load_seconds=round(load_seconds, 2), **result,
        ), indent=2))
        return

    with inference_mode():
        rows = compare(classify)
    print(json.dumps(dict(checkpoint=args.model_directory.name, device="cpu", threads=args.threads,
        load_seconds=round(load_seconds, 2), median_ms=statistics.median(r["milliseconds"] for r in rows),
        model_correct=sum(r["prediction"] == r["expected"] for r in rows),
        rules_correct=sum(r["enforced"] == r["expected"] for r in rows), rows=rows), indent=2))


if __name__ == "__main__":
    main()
