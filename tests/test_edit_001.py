import pytest
import harness as h
from scripts.codex_role import _validate_edit, _write_result


def test_edit_validation():
    before = "def advance(x): return x"
    _validate_edit(before, "def advance(x): return x + 1")
    with pytest.raises(ValueError, match="FULL review"):
        _validate_edit(before, "def advance(x, y): return x + y")
    with pytest.raises(ValueError, match="unchanged"):
        _validate_edit(before, before)


def test_no_write_is_detected(tmp_path):
    h.git("init", "-q", cwd=tmp_path)
    h.git("-c","user.name=Test","-c","user.email=test@localhost","commit","--allow-empty","-qm","base",cwd=tmp_path)
    with pytest.raises(ValueError, match="without changing"):
        _write_result("HEAD", tmp_path)
    (tmp_path/"owned.py").write_text("x = 1")
    assert _write_result("HEAD", tmp_path) == ["owned.py"]
