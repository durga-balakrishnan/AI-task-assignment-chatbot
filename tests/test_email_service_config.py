import email_service
import app


def test_email_settings_use_requested_variable_names(monkeypatch):
    monkeypatch.setenv("SMTP_HOST", "smtp.gmail.com")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_EMAIL", "test@example.com")
    monkeypatch.setenv("SMTP_APP_PASSWORD", "PASTE_APP_PASSWORD_HERE")
    monkeypatch.setenv("EMAIL_DEMO_MODE", "false")

    config = email_service.get_email_config()

    assert config["host"] == "smtp.gmail.com"
    assert config["port"] == "587"
    assert config["email"] == "test@example.com"
    assert config["demo_mode"] is False
    assert email_service.has_smtp_credentials() is False


def test_placeholder_password_is_not_used_to_send(monkeypatch):
    monkeypatch.setenv("EMAIL_DEMO_MODE", "false")
    monkeypatch.setenv("SMTP_EMAIL", "test@example.com")
    monkeypatch.setenv("SMTP_APP_PASSWORD", "PASTE_APP_PASSWORD_HERE")

    result = email_service.send_assignment_email(
        "Task", "Description", "High", "2026-11-01", "Employee", "employee@example.com"
    )

    assert result["success"] is False
    assert "Replace PASTE_APP_PASSWORD_HERE" in result["message"]


def test_settings_password_status_does_not_depend_on_module_helper(monkeypatch):
    config = {
        "host": "smtp.gmail.com",
        "email": "test@example.com",
        "password": "PASTE_APP_PASSWORD_HERE",
        "demo_mode": False,
    }
    monkeypatch.setattr(app.email_service, "get_email_config", lambda: config)
    monkeypatch.setattr(app.ollama_explainer, "get_ollama_config", lambda: {
        "model": "gemma3:4b",
        "endpoint": "http://localhost:11434",
    })

    class FakeStreamlit:
        def __init__(self):
            self.writes = []

        def subheader(self, value):
            pass

        def write(self, value):
            self.writes.append(value)

    fake_st = FakeStreamlit()
    monkeypatch.setattr(app, "st", fake_st)
    monkeypatch.delattr(app.email_service, "has_smtp_credentials")

    app.render_settings()

    email_status = next(item for item in fake_st.writes if isinstance(item, dict) and "SMTP password configured" in item)
    assert email_status["SMTP password configured"] is False
