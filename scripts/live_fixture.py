"""Exercise the architect, engineer and reviewer roles using the approved FEAT-042 fixture."""
import json
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import harness as h
from demo import commit


def main():
    base = h.clean_revision()
    folder = Path(".harness/live").resolve() / uuid.uuid4().hex
    folder.mkdir(parents=True)
    print(f"Run {folder}", flush=True)

    def ask(role, model, prompt):
        out = folder / (role + ".txt")
        start = time.monotonic()
        cmd = [sys.executable, "scripts/codex_project.py", "exec", "-s", "read-only", "--ephemeral",
               "--json", "-m", model, "-o", str(out), "-"]
        result = subprocess.run(cmd, input=prompt, capture_output=True, text=True,
                                encoding="utf-8", errors="replace", timeout=300)
        events = []
        for line in result.stdout.splitlines():
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if "usage" in event or event.get("type") == "error":
                events.append(event)
        (folder / (role + ".metrics.json")).write_text(json.dumps(dict(model=model, events=events,
            seconds=round(time.monotonic()-start, 2), prompt_chars=len(prompt)), indent=2))
        if result.returncode:
            raise ValueError((result.stderr + result.stdout)[-2000:])
        answer = out.read_text(encoding="utf-8").strip()
        print(f"{role} finished", flush=True)
        return answer

    architect = "gpt-6.2-astra"
    engineer = "gpt-6.2-sol"
    expected = h.Ticket.model_validate_json(Path("tickets/FEAT-042.json").read_bytes())
    answer = ask("intent", architect, "Use only supplied context. Return one JSON ticket, without markdown. "
        "Preserve the given IDs, requirements and scope exactly. Write the objective concisely. "
        + expected.model_dump_json() + "\nCatalog: " + h.catalog().model_dump_json())
    ticket = h.Ticket.model_validate_json(answer)
    if ticket.model_copy(update={"intent": expected.intent}) != expected:
        raise ValueError("Architect changed approved fixture obligations")
    compiled = h.compile_ticket(ticket)
    contract = compiled["contract"]
    source = Path("fixture/combat.py").read_text()
    proposal = json.loads(ask("proposal", engineer,
        "Return only JSON with two fields: material (boolean) and rationale (string). "
        "Determine whether this fixture needs a public interface, dependency or scope change. "
        "Use only supplied evidence. " + json.dumps(compiled["task"])))
    if proposal.get("material") is not False:
        raise ValueError("Material proposal requires a revised contract and architect approval")
    tree = folder / "attempt"
    h.git("worktree", "add", "--detach", str(tree), base)
    shutil.copyfile("examples/test_feat_042.py.in", tree / compiled["task"]["acceptance_file"])
    commit(tree, "Add reviewer-controlled fixture acceptance examples")
    receipt = h.Receipt.model_validate_json(Path("examples/receipt.json").read_bytes())
    red = h.verify(contract, tree, receipt)
    (folder / "red.json").write_text(json.dumps(red, indent=2))
    if red["checks"]["pytest"]["exit"] != 1:
        raise ValueError("Expected failing baseline")
    answer = ask("implementation", engineer,
        "Return only JSON with a single string field named source containing the complete updated "
        "fixture/combat.py. Keep the public API and imports. Use only supplied input and no tools. "
        + json.dumps(compiled["task"]) + "\nCurrent file:\n" + source)
    candidate = json.loads(answer)["source"]
    (tree / "fixture/combat.py").write_text(candidate, encoding="utf-8")
    commit(tree, "Implement the approved poison fixture intent")
    result = h.verify(contract, tree, receipt)
    (folder / "review.json").write_text(json.dumps(result, indent=2))
    if not result["passed"]:
        raise ValueError(result["problems"])
    diff = h.git("diff", base, result["revision"], "--", cwd=tree)
    answer = ask("decision", architect, "Review the supplied intent, passing evidence, proposal and diff. "
        "Use only supplied input, no tools. Return only JSON with verdict (approve or revise) and reason. "
        + json.dumps([result, proposal, diff]))
    if json.loads(answer).get("verdict") != "approve":
        raise ValueError("Reviewer requested revision")
    print(f"Approved {result['revision']}", flush=True)


if __name__ == "__main__":
    main()
