import os
from email.message import EmailMessage
from typing import Dict, Optional

from dotenv import load_dotenv
import smtplib


load_dotenv()


def get_email_config() -> Dict[str, str]:
    return {
        "host": os.getenv("SMTP_HOST", "smtp.gmail.com"),
        "port": str(os.getenv("SMTP_PORT", "587")),
        "email": os.getenv("SMTP_EMAIL", "bdurgabalakrishnan@gmail.com"),
        "password": os.getenv("SMTP_APP_PASSWORD", ""),
        "demo_mode": str(os.getenv("EMAIL_DEMO_MODE", "false")).lower() == "true",
    }

def has_smtp_credentials() -> bool:
    config = get_email_config()
    password = config["password"].strip()
    return bool(config["email"].strip() and password and password.upper() != "PASTE_APP_PASSWORD_HERE")


def build_assignment_email(task_title: str, description: str, priority: str, deadline: str, employee_name: str, employee_email: str) -> Dict[str, str]:
    subject = f"New Task Assignment – {task_title}"
    body = (
        f"Hello {employee_name},\n\n"
        f"You have been assigned the {task_title} task.\n\n"
        f"Task: {task_title}\n"
        f"Description: {description}\n"
        f"Priority: {priority}\n"
        f"Deadline: {deadline}\n\n"
        "Please review the requirements and complete the task by the specified deadline.\n\n"
        "Regards,\n"
        "Task Assignment Chatbot"
    )
    return {"subject": subject, "body": body, "recipient": employee_email}


def send_assignment_email(task_title: str, description: str, priority: str, deadline: str, employee_name: str, employee_email: str) -> Dict[str, object]:
    config = get_email_config()
    if config["demo_mode"]:
        return {
            "success": True,
            "message": "Demo mode enabled. Email preview generated but not sent.",
            "demo_mode": True,
        }

    smtp_email = config["email"].strip()
    smtp_password = "".join(config["password"].split())
    if not smtp_email or not smtp_password or smtp_password.upper() == "PASTE_APP_PASSWORD_HERE":
        return {
            "success": False,
            "message": "SMTP email credentials are not configured. Replace PASTE_APP_PASSWORD_HERE in .env with your Gmail App Password.",
            "demo_mode": False,
        }

    try:
        smtp_host = config["host"].strip()
        smtp_port = int(config["port"].strip())
        msg = EmailMessage()
        msg["From"] = smtp_email
        msg["To"] = employee_email
        msg["Subject"] = f"New Task Assignment – {task_title}"
        msg.set_content(
            f"Hello {employee_name},\n\n"
            f"You have been assigned the {task_title} task.\n\n"
            f"Task: {task_title}\n"
            f"Description: {description}\n"
            f"Priority: {priority}\n"
            f"Deadline: {deadline}\n\n"
            "Please review the requirements and complete the task by the specified deadline.\n\n"
            "Regards,\n"
            "Task Assignment Chatbot"
        )

        if smtp_port == 465:
            server_context = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
        elif smtp_port == 587:
            server_context = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
        else:
            raise ValueError("SMTP_PORT must be 465 (SSL) or 587 (STARTTLS).")

        with server_context as server:
            if smtp_port == 587:
                server.ehlo()
                server.starttls()
                server.ehlo()
            server.login(smtp_email, smtp_password)
            server.send_message(msg)

        return {"success": True, "message": "Email sent successfully.", "demo_mode": False}
    except Exception as exc:  # pragma: no cover - network errors are handled by caller
        return {"success": False, "message": f"Failed to send email: {exc}", "demo_mode": False}
