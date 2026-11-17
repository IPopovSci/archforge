"""Replay synthetic changes in a fresh detached worktree and retain its evidence."""
import json
import shutil
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as h


def commit(tree, message):
    h.git("add", "-A", cwd=tree)
    h.git("-c", "user.name=Harness Fixture", "-c", "user.email=harness@localhost",
          "commit", "-m", message, cwd=tree)


def main():
    base = h.clean_revision()
    ticket = h.Ticket.model_validate_json(Path("tickets/FEAT-042.json").read_bytes())
    compiled = h.compile_ticket(ticket)
    contract = compiled["contract"]
    receipt = h.Receipt.model_validate_json(Path("examples/receipt.json").read_bytes())
    folder = Path(".harness/runs").resolve() / uuid.uuid4().hex
    folder.mkdir(parents=True)
    tree = folder / "attempt"
    h.git("worktree", "add", "--detach", str(tree), base)

    def save(name, value):
        (folder / (name + ".json")).write_text(json.dumps(value, indent=2), encoding="utf-8")

    # Characterize the starting behavior before applying the feature.
    combat = tree / "fixture/combat.py"
    original = combat.read_text()
    tests = tree / compiled["task"]["acceptance_file"]
    shutil.copyfile("examples/test_feat_042.py.in", tests)
    commit(tree, "Demonstrate failing acceptance examples")
    red = h.verify(contract, tree, receipt)
    assert red["checks"]["pytest"]["exit"] == 1
    save("red", red)

    combat.write_text(original.replace("poison=(5,)", "poison=entity.poison + (5,)"))
    commit(tree, "Accumulate independent poison durations")
    green = h.verify(contract, tree, receipt)
    save("review", green)
    if not green["passed"]:
        raise ValueError(green["problems"])

    # The native policy must reject a real forbidden import.
    with (tree / "fixture/entities.py").open("a") as f:
        f.write("\nimport fixture.combat\n")
    tach = h.run(h.BIN / "tach", "check", cwd=tree, check=False)
    assert tach.returncode and "fixture.combat" in (tach.stdout + tach.stderr)
    save("forbidden_import", {"exit": tach.returncode, "output": tach.stdout + tach.stderr})
    commit(tree, "Exercise out-of-scope and forbidden dependency detection")
    rejected = h.verify(contract, tree, receipt)
    assert not rejected["passed"]
    save("scope_rejected", rejected)

    # Replay bypass profiles on real Git diffs in the same disposable worktree.
    before = h.clean_revision(tree)
    with (tree / "README.md").open("a") as f:
        f.write("\nFixture documentation correction.\n")
    fast = h.profile(h.diff_paths(before, tree))
    assert fast == "FAST"
    commit(tree, "Exercise documentation bypass")
    before = h.clean_revision(tree)
    entity = tree / "fixture/entities.py"
    entity.write_text(entity.read_text().replace("import fixture.combat", ""))
    standard = h.profile(h.diff_paths(before, tree))
    assert standard == "STANDARD"
    h.run(h.BIN / "tach", "check", cwd=tree)
    h.run(sys.executable, "-m", "pytest", "-q", "tests/test_regression.py", cwd=tree)
    commit(tree, "Repair isolated dependency regression")
    save("profiles", {"FAST": fast, "STANDARD": standard, "cloud_calls": 0})
    print(f"Verified {green['revision']}. Evidence: {folder}")


if __name__ == "__main__":
    main()
