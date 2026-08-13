import tomllib
from pathlib import Path

from app.config import Settings


def test_release_versions_match() -> None:
    version_file = Path("VERSION").read_text(encoding="utf-8").strip()
    with Path("pyproject.toml").open("rb") as project_file:
        project_version = tomllib.load(project_file)["project"]["version"]

    assert version_file == "0.1.0"
    assert project_version == version_file
    assert Settings.model_fields["app_version"].default == version_file
