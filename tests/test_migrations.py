from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


def test_alembic_has_single_baseline_head() -> None:
    config = Config("alembic.ini")
    script = ScriptDirectory.from_config(config)

    assert script.get_heads() == ["20260813_0001"]
    assert script.get_base() == "20260813_0001"
    assert Path("alembic/versions/20260813_0001_baseline.py").is_file()
