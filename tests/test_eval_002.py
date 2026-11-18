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
