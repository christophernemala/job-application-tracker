import importlib


def test_profile_and_preferences_present():
    from job_agent.config import JOB_SEARCH_PREFERENCES, USER_PROFILE

    assert USER_PROFILE["name"] == "Christopher Nemala"
    assert USER_PROFILE["email"] == "christophernemala@gmail.com"
    assert JOB_SEARCH_PREFERENCES["minimum_salary_aed"] == 12000


def test_config_env_override(monkeypatch):
    monkeypatch.setenv("NAUKRI_GULF_EMAIL", "override@example.com")
    monkeypatch.setenv("NAUKRI_GULF_PASSWORD", "secret")

    import job_agent.config as cfg

    importlib.reload(cfg)
    email, password = cfg.get_naukri_gulf_credentials()

    assert email == "override@example.com"
    assert password == "secret"
    snapshot = cfg.get_runtime_config_snapshot()
    assert snapshot["naukri_gulf_password_set"] is True


def test_missing_password_raises(monkeypatch):
    monkeypatch.setenv("NAUKRI_GULF_EMAIL", "override@example.com")
    monkeypatch.delenv("NAUKRI_GULF_PASSWORD", raising=False)

    import job_agent.config as cfg

    importlib.reload(cfg)

    try:
        cfg.get_naukri_gulf_credentials()
        assert False, "Expected RuntimeError when password is missing"
    except RuntimeError as exc:
        assert "NAUKRI_GULF_PASSWORD" in str(exc)
