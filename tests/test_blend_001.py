from scripts import shadow_decisions as s


def test_decisive_signal():
    def unused(*args):
        raise AssertionError("decisive evidence must bypass inference")
    for paths, observed, floor in [
        (["README.md"],None,"FAST"), (["tach.toml"],None,"FULL"),
        (["tests/test_regression.py"],None,"STANDARD"),
        (["fixture/combat.py"],"FULL","FULL"), (["tach.toml"],"STANDARD","FULL"),
    ]:
        row = s._assess("task", paths, observed, unused)
        assert row["floor"] == row["recommendation"] == floor
        assert not row["model_called"]


def test_ambiguous_signal():
    paths = ["harness.py"]
    def classify(*args):
        return {"workflow":"architecture or interface design"}
    row = s._assess("reshape caller contract", paths, None, classify)
    assert row["recommendation"] == "FULL" and row["floor"] == "STANDARD" and row["model_called"]
    for prediction in ("documentation correction","unrecognized"):
        row = s._assess("adjust compiler",paths,None,lambda *_: {"workflow":prediction})
        assert row["recommendation"] == "STANDARD"
    no_model = s._assess("adjust compiler",paths,None,None)
    assert no_model["abstained"] and not no_model["model_called"]


def test_comparison():
    result = s._benchmark(lambda *_: {"workflow":"contained implementation fix"})
    for treatment in ("path_rules","deterministic","model_only","selective"):
        assert result["metrics"][treatment]["total"] == len(result["rows"])
        assert "missed_full" in result["metrics"][treatment]
    assert len(result["rows"]) >= 12
    assert 0 < result["metrics"]["selective"]["model_calls"] < len(result["rows"])
    assert len({r["request"] for r in result["rows"]} & {r[0] for r in s.CASES}) == 0
