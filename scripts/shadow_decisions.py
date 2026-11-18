"""Offline CPU experiment. Predictions are advisory and never execute a routing action."""
import argparse
import ast as _ast
import contextlib as _contextlib
import json
import os
import re as _re
import statistics
import subprocess as _subprocess
import sys
import time
import tokenize as _tokenize
from pathlib import Path
from collections.abc import Mapping as _Mapping

# The experimental CLI imports its harness in a fresh process in the reference checkout.
if __name__ != "__main__" or "--embedding-study" not in sys.argv[1:]:
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


_EMBEDDING_RETRIEVAL_CASES = (
    ("ticket_digest", "harness.py#ticket_digest"),
    ("compile_ticket", "harness.py#compile_ticket"),
    ("apply_poison", "fixture/combat.py#apply_poison"),
    ("public_api_digest", "harness.py#public_api_digest"),
    ("Which check catches a work order whose approval was signed for another revision?",
     "harness.py#_validate_review"),
    ("Find edits someone made that Git is not tracking yet", "harness.py#diff_paths"),
    ("Where do we catch a worker that said done but touched nothing?",
     "scripts/codex_role.py#_write_result"),
    ("Where is an isolated engineer conversation started and its identity recorded?",
     "scripts/codex_role.py#invoke"),
    ("How are passing examples matched to each promised behavior?", "harness.py#verify"),
    ("Prevent a proposed rewrite from silently changing the callable interface",
     "scripts/codex_role.py#_validate_edit"),
    ("Collect a few source snippets relevant to the request", "harness.py#_context"),
    ("Tick down the remaining lifetime and apply damage for this simulation step",
     "fixture/turn_lifecycle.py#advance"),
)
_EMBEDDING_EXACT_COUNT = 4
_EMBEDDING_CUTOFF = 20
_EMBEDDING_RRF_K = 60
_EMBEDDING_BGE_PREFIX = "Represent this sentence for searching relevant passages: "


def _fuse(list1, list2):
    scores = {}
    for ranking in (list1, list2):
        seen = set()
        for rank, symbol in enumerate(ranking, 1):
            if symbol is None or symbol in seen:
                continue
            seen.add(symbol)
            scores[symbol] = scores.get(symbol, 0.0) + 1 / (_EMBEDDING_RRF_K + rank)
    return sorted(scores, key=lambda symbol: (-scores[symbol], symbol))


def _rank_metrics(ranks):
    ranks = list(ranks)
    return {
        "top1": sum(rank == 1 for rank in ranks),
        "top3": sum(rank is not None and rank <= 3 for rank in ranks),
        "mrr": sum(1 / rank for rank in ranks if rank is not None) / len(ranks) if ranks else 0.0,
    }


def _embedding_suggestion(floor, predicted):
    return max(floor, predicted, key=_PROFILES.index)


def _embedding_git(root, *args):
    result = _subprocess.run(
        ["git", "--no-optional-locks", *args], cwd=root, capture_output=True, check=False,
    )
    if result.returncode:
        raise ValueError(os.fsdecode(result.stderr).strip() or f"Git {args[0]} failed")
    return os.fsdecode(result.stdout)


def _embedding_revision(root):
    top = Path(_embedding_git(root, "rev-parse", "--show-toplevel").rstrip("\r\n")).resolve()
    if top != root:
        raise ValueError("Run the embedding study from the root of the reference checkout")
    if _embedding_git(root, "status", "--porcelain=v1", "--untracked-files=all", "--ignore-submodules=none"):
        raise ValueError("The reference Git checkout is dirty")
    return _embedding_git(root, "rev-parse", "--verify", "HEAD").strip()


# A separate interpreter resolves harness.py and its imports from the reference checkout.
_EMBEDDING_REFERENCE_WORKER = '''
import json
import sys
import time
import harness

payload = json.load(sys.stdin)
start = time.perf_counter()
catalog = harness.catalog().model_dump()
catalog_seconds = time.perf_counter() - start
start = time.perf_counter()
responses = [json.loads(harness.trail("ask", query, ".", "--json", "-n", str(payload["cutoff"])))
             for query in payload["queries"]]
query_batch_seconds = time.perf_counter() - start
start = time.perf_counter()
rules = harness.RuleProvider()
floors = [rules.decide(paths, payload["profiles"])["choice"] for paths in payload["paths"]]
print(json.dumps({"catalog": catalog, "responses": responses, "floors": floors,
                  "timings": {"catalog_seconds": catalog_seconds,
                              "query_batch_seconds": query_batch_seconds,
                              "path_floor_seconds": time.perf_counter() - start}}))
'''


def _embedding_reference(root):
    payload = dict(
        queries=[query for query, _ in _EMBEDDING_RETRIEVAL_CASES],
        paths=[paths for _, paths, _, _ in _SELECTIVE_CASES],
        profiles=_PROFILES,
        cutoff=_EMBEDDING_CUTOFF,
    )
    process = _subprocess.run(
        [sys.executable, "-B", "-X", "utf8", "-c", _EMBEDDING_REFERENCE_WORKER],
        cwd=root, input=json.dumps(payload), encoding="utf-8", errors="replace",
        capture_output=True, check=False,
    )
    if process.returncode:
        raise ValueError(process.stderr.strip() or "The reference harness failed")
    return json.loads(process.stdout)


def _embedding_relative_path(root, value):
    if not isinstance(value, str) or not value:
        return None
    path = Path(value.replace("\\", "/"))
    try:
        return (root / path).resolve().relative_to(root).as_posix()
    except ValueError:
        return None


def _embedding_module_paths(root, catalog, tracked):
    return (set(catalog["modules"].values()) & tracked) - {"scripts/shadow_decisions.py"}


def _embedding_words(text):
    text = _re.sub(r"([A-Z])([A-Z][a-z])", r"\1 \2", text)
    text = _re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", text)
    return _re.findall(r"[^\W_]+", text.casefold())


def _embedding_read_module(path):
    with _tokenize.open(path) as handle:
        source = handle.read()
    functions = [node for node in _ast.walk(_ast.parse(source, filename=str(path)))
                 if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef))]
    return source.splitlines(), functions


def _embedding_function_text(path, name, function, excerpt):
    prefix = "async def" if isinstance(function, _ast.AsyncFunctionDef) else "def"
    type_params = getattr(function, "type_params", ())
    generics = "[" + ", ".join(map(_ast.unparse, type_params)) + "]" if type_params else ""
    signature = f"{prefix} {function.name}{generics}({_ast.unparse(function.args)})"
    if function.returns is not None:
        signature += f" -> {_ast.unparse(function.returns)}"
    doc = _ast.get_docstring(function) or ""
    heading = f"{path} {' '.join(_embedding_words(name))}"
    return "\n".join((heading[:250], signature[:300], doc[:200], excerpt))[:1000]


def _embedding_corpus(root, catalog, tracked, *, study=True):
    module_paths = _embedding_module_paths(root, catalog, tracked)
    if not study:
        module_paths = set(catalog["modules"].values()) & tracked
    graph_path = root / "graft/.graph/wiring.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8-sig"))
    nodes = graph.get("nodes") if isinstance(graph, _Mapping) else None
    if nodes is None and isinstance(graph, _Mapping) and isinstance(graph.get("graph"), _Mapping):
        nodes = graph["graph"].get("nodes")
    if isinstance(nodes, _Mapping):
        nodes = [dict(node, id=node.get("id", key)) for key, node in nodes.items()]
    if not isinstance(nodes, list):
        raise ValueError(f"Expected function nodes in {graph_path.relative_to(root)}")

    modules = {}
    documents = {}
    for node in nodes:
        if not isinstance(node, _Mapping):
            continue
        types = {node.get("kind"), node.get("type")} - {None}
        kinds = {"function", "async_function"} if study else {"function", "async_function", "method"}
        if types and types.isdisjoint(kinds):
            continue
        path = _embedding_relative_path(root, node.get("path"))
        if path not in module_paths:
            continue
        symbol, name, span = (node.get(field) for field in ("id", "name", "span"))
        if not all(isinstance(value, str) and value for value in (symbol, name, span)):
            continue
        bounds = _re.fullmatch(r"L(\d+)(?:-L?(\d+))?", span)
        if bounds is None:
            raise ValueError(f"Invalid Trail source span for {symbol}: {span}")
        first = int(bounds[1])
        last = int(bounds[2] or bounds[1])
        if path not in modules:
            modules[path] = _embedding_read_module(root / path)
        lines, functions = modules[path]
        if not 1 <= first <= last <= len(lines):
            raise ValueError(f"Trail source span is outside {path}: {span}")
        matches = [function for function in functions
                   if function.name == name.rsplit(".", 1)[-1] and first <= function.lineno <= last]
        if not matches:
            if types:
                raise ValueError(f"Trail function {symbol} does not match reference source at {span}")
            continue
        function = min(matches, key=lambda match: (match.lineno, match.col_offset))
        if symbol in documents:
            raise ValueError(f"Duplicate Trail symbol ID: {symbol}")
        excerpt = "\n".join(lines[first - 1:last])
        documents[symbol] = dict(path=path, name=name, first=first, last=last,
                                 text=_embedding_function_text(path, name, function, excerpt))

    missing = sorted({target for _, target in _EMBEDDING_RETRIEVAL_CASES} - documents.keys())
    if study and missing:
        raise ValueError("Retrieval targets missing from the eligible Trail corpus: " + ", ".join(missing))
    return documents, graph_path.relative_to(root).as_posix(), len(module_paths)


def _embedding_trail_hits(response):
    if isinstance(response, list):
        return response, {"response_shape": "array"}
    if isinstance(response, _Mapping):
        for key in ("hits", "results", "matches"):
            if isinstance(response.get(key), list):
                metadata = {field: response[field] for field in ("schema", "schema_version", "protocol")
                            if field in response and isinstance(response[field], (str, int))}
                return response[key], dict(response_shape=key, **metadata)
    raise ValueError("Unsupported Trail ask JSON response: expected an ordered hit list")


def _embedding_trail_symbol(root, hit, documents, by_path):
    if not isinstance(hit, _Mapping):
        return None
    pointer = hit.get("pointer")
    if isinstance(pointer, _Mapping):
        path = pointer.get("path", pointer.get("file"))
        location = str(pointer.get("span") or pointer.get("line") or pointer.get("start_line") or "")
    elif isinstance(pointer, str):
        if pointer in documents:
            return pointer
        match = _re.fullmatch(r"(.+?\.py)(?:[:#](.*))?", pointer.strip(), _re.IGNORECASE)
        if match is None:
            return None
        path, location = match[1], match[2] or ""
    else:
        return None
    path = _embedding_relative_path(root, path)
    candidates = by_path.get(path, ())
    anchor = _re.match(r"L?(\d+)", location)
    if anchor:
        line = int(anchor[1])
        candidates = [symbol for symbol in candidates
                      if documents[symbol]["first"] <= line <= documents[symbol]["last"]]
    elif location and f"{path}#{location}" in documents:
        return f"{path}#{location}"

    title = hit.get("title")
    tokens = set(_re.findall(r"\w+", title)) if isinstance(title, str) else set()
    named = [symbol for symbol in candidates if documents[symbol]["name"].rsplit(".", 1)[-1] in tokens]
    if len(named) == 1:
        return named[0]
    if anchor and not named and len(candidates) == 1:
        return candidates[0]
    return None


def _embedding_trail_rankings(root, responses, documents):
    by_path = {}
    for symbol, document in documents.items():
        by_path.setdefault(document["path"], []).append(symbol)
    rankings = []
    for response in responses:
        hits, protocol = _embedding_trail_hits(response)
        ranking = [_embedding_trail_symbol(root, hit, documents, by_path)
                   for hit in hits[:_EMBEDDING_CUTOFF]]
        rankings.append((ranking, protocol))
    return rankings


def _embedding_tfidf_index(vectorizer_type, texts):
    vectorizer = vectorizer_type(tokenizer=_embedding_words, token_pattern=None,
                                lowercase=False, ngram_range=(1, 2))
    return vectorizer.fit_transform(texts), vectorizer.transform


def _embedding_encoder(directory, torch, tokenizer_type, model_type, pooling):
    options = dict(local_files_only=True, trust_remote_code=False)
    tokenizer = tokenizer_type.from_pretrained(str(directory), **options)
    model = model_type.from_pretrained(str(directory), **options).to("cpu").eval()

    def encode(texts):
        batches = []
        with torch.inference_mode():
            for start in range(0, len(texts), 16):
                inputs = tokenizer(texts[start:start + 16], padding=True, truncation=True,
                                   max_length=256, return_tensors="pt")
                hidden = model(**inputs).last_hidden_state
                if pooling == "masked_mean":
                    mask = inputs["attention_mask"].unsqueeze(-1).to(hidden.dtype)
                    pooled = (hidden * mask).sum(dim=1) / mask.sum(dim=1).clamp_min(1)
                else:
                    pooled = hidden[:, 0]
                batches.append(torch.nn.functional.normalize(pooled.float(), p=2, dim=1))
        return torch.cat(batches, dim=0).numpy()

    return encode


def _embedding_score_batch(index, texts, queries):
    start = time.perf_counter()
    indexed, encode = index(texts)
    index_seconds = time.perf_counter() - start
    start = time.perf_counter()
    scores = encode(queries) @ indexed.T
    if hasattr(scores, "toarray"):
        scores = scores.toarray()
    scores = scores.tolist()
    return scores, dict(index_seconds=index_seconds, query_batch_seconds=time.perf_counter() - start)


def _embedding_evaluate(index, documents, retrieval_prefix=""):
    symbols = sorted(documents)
    retrieval_scores, retrieval_timing = _embedding_score_batch(
        index, [documents[symbol]["text"] for symbol in symbols],
        [retrieval_prefix + query for query, _ in _EMBEDDING_RETRIEVAL_CASES],
    )
    routing_scores, routing_timing = _embedding_score_batch(
        index, [request for request, _, _ in CASES],
        [request for request, _, _, _ in _SELECTIVE_CASES],
    )
    rankings = []
    for scores in retrieval_scores:
        ordered = sorted(zip(symbols, scores), key=lambda item: (-item[1], item[0]))
        rankings.append([symbol for symbol, _ in ordered[:_EMBEDDING_CUTOFF]])
    neighbors = [max(range(len(CASES)), key=scores.__getitem__) for scores in routing_scores]
    return dict(rankings=rankings, neighbors=neighbors,
                timings=dict(retrieval=retrieval_timing, routing=routing_timing))


def _embedding_retrieval_report(trail, evaluations):
    rows = []
    for index, (query, target) in enumerate(_EMBEDDING_RETRIEVAL_CASES):
        trail_ranking, protocol = trail[index]
        rankings = {name: evaluation["rankings"][index] for name, evaluation in evaluations.items()}
        rankings.update(trail=trail_ranking)
        for name in ("minilm", "bge"):
            rankings[f"trail_{name}_rrf"] = _fuse(trail_ranking, rankings[name])[:_EMBEDDING_CUTOFF]
        ranks = {name: ranking.index(target) + 1 if target in ranking else None
                 for name, ranking in rankings.items()}
        rows.append(dict(
            query=query, target_id=target, group="exact" if index < _EMBEDDING_EXACT_COUNT else "paraphrase",
            ranks=ranks, trail_protocol=protocol, trail_top20=trail_ranking,
            unmapped_trail_positions=[position for position, symbol in enumerate(trail_ranking, 1)
                                      if symbol is None],
        ))

    metrics = {}
    for group in ("exact", "paraphrase"):
        metrics[group] = {}
        for name in rows[0]["ranks"]:
            ranks = [row["ranks"][name] for row in rows if row["group"] == group]
            metrics[group][name] = dict(total=len(ranks), missing=ranks.count(None), **_rank_metrics(ranks))
    return dict(rows=rows, metrics=metrics)


def _embedding_routing_metrics(rows, name, field):
    labeled = [(row["expected"], row["predictions"][name][field]) for row in rows]
    return dict(
        total=len(labeled),
        correct=sum(expected == predicted for expected, predicted in labeled),
        missed_full=sum(expected == "FULL" and predicted != "FULL" for expected, predicted in labeled),
        unnecessary_full=sum(expected != "FULL" and predicted == "FULL" for expected, predicted in labeled),
        unnecessary_promotions=sum(_PROFILES.index(predicted) > _PROFILES.index(expected)
                                   for expected, predicted in labeled),
    )


def _embedding_routing_report(floors, evaluations):
    rows = []
    for index, (request, paths, expected, _) in enumerate(_SELECTIVE_CASES):
        floor = floors[index]
        predictions = {"path_only": dict(raw=floor, floor_constrained=floor)}
        for name, evaluation in evaluations.items():
            neighbor = evaluation["neighbors"][index]
            training_request, _, raw = CASES[neighbor]
            predictions[name] = dict(raw=raw, floor_constrained=_embedding_suggestion(floor, raw),
                                     nearest_training_request=training_request)
        rows.append(dict(request=request, paths=paths, expected=expected, path_floor=floor,
                         predictions=predictions))
    metrics = {
        name: {field: _embedding_routing_metrics(rows, name, field)
               for field in ("raw", "floor_constrained")}
        for name in ("path_only", *evaluations)
    }
    return dict(rows=rows, metrics=metrics)


def _embedding_study(model_directories, threads):
    root = Path.cwd().resolve()
    revision = _embedding_revision(root)
    tracked = set(_embedding_git(root, "ls-files", "-z").split("\0"))
    models = {name: directory.resolve()
              for name, directory in zip(("minilm", "bge"), model_directories)}
    for name, directory in models.items():
        if not directory.is_dir():
            raise ValueError(f"Expected a local {name} model directory: {directory}")

    training_requests = {" ".join(request.casefold().split()) for request, _, _ in CASES}
    test_requests = {" ".join(request.casefold().split()) for request, _, _, _ in _SELECTIVE_CASES}
    if training_requests & test_requests:
        raise ValueError("Embedding routing training and test requests overlap")

    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1",
                      TOKENIZERS_PARALLELISM="false", OMP_NUM_THREADS=str(threads),
                      MKL_NUM_THREADS=str(threads), OPENBLAS_NUM_THREADS=str(threads))
    reference = _embedding_reference(root)
    start = time.perf_counter()
    documents, graph_path, module_count = _embedding_corpus(root, reference["catalog"], tracked)
    corpus_seconds = time.perf_counter() - start
    trail = _embedding_trail_rankings(root, reference["responses"], documents)

    start = time.perf_counter()
    from sklearn.feature_extraction.text import TfidfVectorizer

    timings = {"tfidf": {"load_seconds": time.perf_counter() - start}}

    def tfidf_index(texts):
        return _embedding_tfidf_index(TfidfVectorizer, texts)

    evaluations = {"tfidf": _embedding_evaluate(tfidf_index, documents)}
    start = time.perf_counter()
    import torch
    from transformers import AutoModel, AutoTokenizer

    torch.set_num_threads(threads)
    torch.set_num_interop_threads(1)
    encoder_import_seconds = time.perf_counter() - start
    for name, pooling, prefix in (("minilm", "masked_mean", ""), ("bge", "cls", _EMBEDDING_BGE_PREFIX)):
        start = time.perf_counter()
        encode = _embedding_encoder(models[name], torch, AutoTokenizer, AutoModel, pooling)
        timings[name] = {"load_seconds": time.perf_counter() - start}

        def dense_index(texts):
            return encode(texts), encode

        evaluations[name] = _embedding_evaluate(dense_index, documents, prefix)
        del encode

    for name, evaluation in evaluations.items():
        timings[name].update(evaluation["timings"])
    if _embedding_revision(root) != revision:
        raise ValueError("The reference Git revision changed during the study")
    return dict(
        corpus_revision=revision, graph_path=graph_path, device="cpu", threads=threads,
        torch_interop_threads=1, model_directories={name: str(path) for name, path in models.items()},
        counts=dict(catalog_modules=module_count, indexed_modules=len({doc["path"] for doc in documents.values()}),
                    candidates=len(documents), retrieval_queries=len(_EMBEDDING_RETRIEVAL_CASES),
                    routing_training=len(CASES), routing_test=len(_SELECTIVE_CASES)),
        protocol=dict(trail_arguments=["ask", "<query>", ".", "--json", "-n", str(_EMBEDDING_CUTOFF)],
                      rank_cutoff=_EMBEDDING_CUTOFF, rrf_k=_EMBEDDING_RRF_K,
                      unmapped_trail_hits="retain original rank positions", routing_floor="intended paths",
                      routing_training="CASES", routing_test="_SELECTIVE_CASES", routing_disjoint=True,
                      document_character_cap=1000, encoder_token_cap=256, encoder_batch_size=16),
        timings=dict(corpus_seconds=corpus_seconds, reference=reference["timings"],
                     encoder_import_seconds=encoder_import_seconds, methods=timings),
        retrieval=_embedding_retrieval_report(trail, evaluations),
        routing=_embedding_routing_report(reference["floors"], evaluations),
    )


def _lookup_hits(documents, scores, revision):
    ordered = sorted(zip(sorted(documents), scores, strict=True), key=lambda pair: (-pair[1], pair[0]))
    hits = []
    for symbol, score in ordered[:3]:
        doc = documents[symbol]
        hits.append(dict(symbol=symbol, pointer=f"{doc['path']}:L{doc['first']}-L{doc['last']}",
                         revision=revision, cosine=float(score), excerpt=doc["text"][:650]))
    return hits


def _semantic_lookup(query, directory, threads):
    from harness import catalog
    if not query.strip() or len(query) > 1000 or not directory.is_dir():
        raise ValueError("Provide a short question and an installed MiniLM checkpoint directory")
    import torch
    from transformers import AutoModel, AutoTokenizer
    root = Path.cwd().resolve()
    cat = catalog()
    tracked = set(_embedding_git(root, "ls-files", "-z").split("\0"))
    documents, _, _ = _embedding_corpus(root, cat.model_dump(), tracked, study=False)
    if not documents:
        raise ValueError("No indexed functions in the current catalog")
    torch.set_num_threads(threads)
    encode = _embedding_encoder(directory, torch, AutoTokenizer, AutoModel, "masked_mean")
    indexed = encode([documents[symbol]["text"] for symbol in sorted(documents)])
    scores = (encode([query]) @ indexed.T)[0]
    if _embedding_revision(root) != cat.revision:
        raise ValueError("Revision changed during lookup")
    return _lookup_hits(documents, scores, cat.revision)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_directory", nargs="?", type=Path, help="Local model checkpoint")
    parser.add_argument("--threads", type=int, default=4, help="CPU thread count")
    parser.add_argument("--request", help="Assess one engineering request")
    parser.add_argument("--paths", nargs="+", help="Intended repository-relative paths")
    parser.add_argument("--base", help="Recheck the diff against this Git revision")
    parser.add_argument("--benchmark-selective", action="store_true", help="Run the selective benchmark")
    parser.add_argument("--semantic-query", help="Return three revision-bound MiniLM source matches")
    parser.add_argument("--embedding-study", nargs=2, type=Path, metavar=("MINILM_DIR", "BGE_DIR"),
                        help="Run the experimental offline retrieval and routing study")
    args = parser.parse_args()
    if args.semantic_query is not None:
        if (args.model_directory is None or args.threads < 1 or args.embedding_study or args.request is not None
                or args.paths or args.base or args.benchmark_selective):
            parser.error("--semantic-query requires a local MiniLM directory and optional positive --threads")
        print(json.dumps(_semantic_lookup(args.semantic_query, args.model_directory, args.threads), indent=2))
        return
    if args.threads < 1:
        parser.error("Expected a positive CPU thread count")
    if args.embedding_study is not None:
        if any(value is not None for value in (args.model_directory, args.request, args.paths, args.base)) \
                or args.benchmark_selective:
            parser.error("--embedding-study can only be combined with --threads")
        try:
            with _contextlib.redirect_stdout(sys.stderr):
                result = _embedding_study(args.embedding_study, args.threads)
            output = json.dumps(result, indent=2, allow_nan=False)
        except (ImportError, OSError, RuntimeError, ValueError) as exc:
            parser.error(str(exc))
        print(output)
        return
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
