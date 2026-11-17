"""Offline CPU experiment. Predictions are advisory and never execute a routing action."""
import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from harness import RuleProvider

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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_directory", type=Path)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--request", help="Evaluate a single engineering request in shadow mode")
    parser.add_argument("--paths", nargs="+", help="Intended repository-relative paths for that request")
    args = parser.parse_args()
    if not args.model_directory.is_dir() or args.threads < 1:
        parser.error("Expected a local checkpoint directory and positive CPU thread count")
    if bool(args.request) != bool(args.paths):
        parser.error("Supply --request and --paths together")
    os.environ["HF_HUB_OFFLINE"] = "1"
    from gliner2 import AutoExtractor
    import torch
    torch.set_num_threads(args.threads)
    start = time.perf_counter()
    model = AutoExtractor.from_pretrained(str(args.model_directory.resolve())).to("cpu").eval()
    load_seconds = time.perf_counter() - start
    with torch.inference_mode():
        cases = [(args.request, args.paths, None)] if args.request else CASES
        rows = compare(model.classify_text, cases)
    if args.request:
        print(json.dumps(dict(checkpoint=args.model_directory.name, load_seconds=round(load_seconds,2),
                              **rows[0]), indent=2))
        return
    print(json.dumps(dict(checkpoint=args.model_directory.name, device="cpu", threads=args.threads,
        load_seconds=round(load_seconds, 2), median_ms=statistics.median(r["milliseconds"] for r in rows),
        model_correct=sum(r["prediction"] == r["expected"] for r in rows),
        rules_correct=sum(r["enforced"] == r["expected"] for r in rows), rows=rows), indent=2))


if __name__ == "__main__":
    main()
