from pathlib import Path


def test_project_layout_exists() -> None:
    assert Path("app.py").exists()
    assert Path("README.md").exists()
    assert Path("requirements.txt").exists()
