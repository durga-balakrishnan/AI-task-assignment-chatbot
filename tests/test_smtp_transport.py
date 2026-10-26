from unittest.mock import patch

import email_service


class FakeSmtp:
    def __init__(self, events):
        self.events = events

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def ehlo(self):
        self.events.append("ehlo")

    def starttls(self):
        self.events.append("starttls")

    def login(self, email, password):
        self.events.append(("login", email, password))

    def send_message(self, message):
        self.events.append("send_message")


def test_port_465_uses_smtp_ssl_and_strips_login_credentials():
    events = []
    fake_smtp = FakeSmtp(events)
    config = {
        "host": "smtp.gmail.com",
        "port": "465",
        "email": " sender@example.com ",
        "password": " app password ",
        "demo_mode": False,
    }

    with (
        patch.object(email_service, "get_email_config", return_value=config),
        patch.object(email_service.smtplib, "SMTP_SSL", return_value=fake_smtp) as smtp_ssl,
        patch.object(email_service.smtplib, "SMTP") as smtp,
    ):
        result = email_service.send_assignment_email(
            "Task", "Description", "High", "2026-11-01", "Employee", "employee@example.com"
        )

    assert result["success"] is True
    smtp_ssl.assert_called_once_with("smtp.gmail.com", 465, timeout=30)
    smtp.assert_not_called()
    assert events == [
        ("login", "sender@example.com", "apppassword"),
        "send_message",
    ]


def test_port_587_uses_starttls_sequence():
    events = []
    fake_smtp = FakeSmtp(events)
    config = {
        "host": "smtp.gmail.com",
        "port": "587",
        "email": "sender@example.com",
        "password": "apppassword",
        "demo_mode": False,
    }

    with (
        patch.object(email_service, "get_email_config", return_value=config),
        patch.object(email_service.smtplib, "SMTP", return_value=fake_smtp) as smtp,
        patch.object(email_service.smtplib, "SMTP_SSL") as smtp_ssl,
    ):
        result = email_service.send_assignment_email(
            "Task", "Description", "High", "2026-11-01", "Employee", "employee@example.com"
        )

    assert result["success"] is True
    smtp.assert_called_once_with("smtp.gmail.com", 587, timeout=30)
    smtp_ssl.assert_not_called()
    assert events == [
        "ehlo",
        "starttls",
        "ehlo",
        ("login", "sender@example.com", "apppassword"),
        "send_message",
    ]
