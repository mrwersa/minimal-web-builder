from pathlib import Path


def test_project_layout_exists() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    assert (repo_root / "app.py").is_file()
    assert (repo_root / "README.md").is_file()
    assert (repo_root / "requirements.txt").is_file()
