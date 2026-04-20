from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_root_env_example_exists():
    env_example = REPO_ROOT / ".env.example"
    assert env_example.exists()


def test_root_env_example_contains_required_keys():
    env_example = REPO_ROOT / ".env.example"
    content = env_example.read_text(encoding="utf-8")
    assert "DASHBOARD_USERNAME=" in content
    assert "NAUKRI_GULF_EMAIL=" in content
    assert "OPENAI_API_KEY=" in content


def test_gitignore_excludes_dependencies_and_env_files():
    gitignore = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert "node_modules/" in gitignore
    assert "/.env" in gitignore
    assert "/.env.local" in gitignore


def test_workflow_runs_syntax_validation_and_tests():
    workflow = (REPO_ROOT / ".github" / "workflows" / "main.yml").read_text(encoding="utf-8")
    assert "python -m compileall job_agent" in workflow
    assert "python -m pytest job_agent/tests/ -v" in workflow
