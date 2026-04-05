import importlib


def test_health_endpoint_reports_safe_flags(monkeypatch):
    monkeypatch.delenv("DASHBOARD_USERNAME", raising=False)
    monkeypatch.delenv("DASHBOARD_USER", raising=False)
    monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)

    import job_agent.app as app_module

    app_module = importlib.reload(app_module)
    client = app_module.app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    payload = response.get_json()
    assert payload["status"] == "ok"
    assert payload["dashboard_auth_configured"] is False
    assert payload["flask_secret_key_configured"] is False


def test_api_requires_401_without_auth(monkeypatch):
    monkeypatch.setenv("DASHBOARD_USERNAME", "admin")
    monkeypatch.setenv("DASHBOARD_PASSWORD", "secret")

    import job_agent.app as app_module

    app_module = importlib.reload(app_module)
    client = app_module.app.test_client()

    response = client.get("/api/config")

    assert response.status_code == 401


def test_login_disabled_until_credentials_configured(monkeypatch):
    monkeypatch.delenv("DASHBOARD_USERNAME", raising=False)
    monkeypatch.delenv("DASHBOARD_USER", raising=False)
    monkeypatch.delenv("DASHBOARD_PASSWORD", raising=False)

    import job_agent.app as app_module

    app_module = importlib.reload(app_module)
    client = app_module.app.test_client()

    response = client.get("/login")

    assert response.status_code == 503
