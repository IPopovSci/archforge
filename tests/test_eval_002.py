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
