import json
import subprocess
import sys

from scripts import shadow_decisions as study


def test_rank_measurement():
    assert study._rank_metrics([1, 3, None]) == {"top1": 1, "top3": 2, "mrr": (1 + 1/3)/3}
    assert study._fuse(["a","b","c"], ["b","c","d"])[0] == "b"


def test_routing_floor():
    assert study._embedding_suggestion("FULL", "STANDARD") == "FULL"
    assert study._embedding_suggestion("STANDARD", "FAST") == "STANDARD"
    assert study._embedding_suggestion("STANDARD", "FULL") == "FULL"


def test_lightweight_import():
    cmd = "import sys,json; from scripts import shadow_decisions; print(json.dumps(sorted(set(sys.modules) & {'torch','transformers','sklearn'})))"
    assert json.loads(subprocess.check_output([sys.executable,"-c",cmd], text=True)) == []


def test_lookup_evidence():
    doc = {"path":"app.py", "first":4, "last":6, "text":"x"*800}
    hits = study._lookup_hits(dict.fromkeys(["s","t","u","v"],doc), [0.1,0.2,0.9,0.5], "rev")
    assert [hit["symbol"] for hit in hits] == ["u","v","t"]
    assert all(hit["pointer"] == "app.py:L4-L6" and hit["revision"] == "rev"
               and len(hit["excerpt"]) <= 650 for hit in hits)


def test_exact_lookup_bypasses_encoder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(study, "_embedding_revision", lambda _: "rev")
    doc = dict(path="app.py", name="save", first=2, last=5, text="def save(): ...")
    monkeypatch.setattr(study, "_snapshot", lambda *_: ({"app.py#save":doc}, True))
    for query in ("save", "app.py#save"):
        out = study._lookup(query, None, 1, "query")
        assert out["method"] == "trail-symbol"
        assert out["hits"][0]["pointer"] == "app.py:L2-L5"


def test_snapshot_and_vector_reuse(tmp_path, monkeypatch):
    from types import SimpleNamespace
    monkeypatch.chdir(tmp_path)
    documents = {"app.py#save": {"text":"def save(): ..."}}
    monkeypatch.setattr(study, "_embedding_revision", lambda _: "rev")
    monkeypatch.setattr(study, "_snapshot", lambda *_: (documents, True))
    monkeypatch.setattr(study, "_model_key", lambda model: model)
    monkeypatch.setitem(sys.modules, "torch", SimpleNamespace(set_num_threads=lambda _: None))
    monkeypatch.setitem(sys.modules, "transformers", SimpleNamespace(AutoModel=None, AutoTokenizer=None))
    calls = []
    def encoder(batch):
        calls.append(batch)
        return SimpleNamespace(tolist=lambda: [[1.0]])
    monkeypatch.setattr(study, "_embedding_encoder", lambda *_: encoder)
    assert not study._lookup(None, "m1", 1, "prepare")["vectors_reused"]
    assert study._lookup(None, "m1", 1, "prepare")["vectors_reused"]
    documents["app.py#save"]["text"] += " changed"
    assert not study._lookup(None, "m1", 1, "prepare")["vectors_reused"]
    assert not study._lookup(None, "m2", 1, "prepare")["vectors_reused"]
    assert len(calls) == 3
