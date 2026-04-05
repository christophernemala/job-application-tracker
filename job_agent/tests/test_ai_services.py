from job_agent import ai_services


def test_loads_groq_key_from_local_env_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("GROQ_API_KEY=groq-from-file\nGROQ_MODEL=llama-test\n")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_MODEL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)

    original_resolve = ai_services.Path.resolve

    def fake_resolve(path_obj):
        if str(path_obj).endswith("ai_services.py"):
            return tmp_path / "ai_services.py"
        return original_resolve(path_obj)

    monkeypatch.setattr(ai_services.Path, "resolve", fake_resolve)
    ai_services._load_local_env()

    settings = ai_services._get_provider_settings()

    assert settings["provider"] == "groq"
    assert settings["api_key"] == "groq-from-file"
    assert settings["model"] == "llama-test"


def test_prefers_groq_when_groq_key_is_present(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")

    settings = ai_services._get_provider_settings()

    assert settings["provider"] == "groq"
    assert settings["base_url"] == "https://api.groq.com/openai/v1"
    assert settings["model"] == "llama-3.3-70b-versatile"


def test_uses_openai_when_groq_key_is_missing(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "openai-test-key")

    settings = ai_services._get_provider_settings()

    assert settings["provider"] == "openai"
    assert settings["model"] == "gpt-4o-mini"


def test_requires_provider_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    try:
        ai_services._get_provider_settings()
        assert False, "Expected RuntimeError when no AI provider key is configured"
    except RuntimeError as exc:
        assert "GROQ_API_KEY" in str(exc)
