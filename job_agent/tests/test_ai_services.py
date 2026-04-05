from job_agent import ai_services


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
