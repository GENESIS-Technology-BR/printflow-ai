from __future__ import annotations

import os
import smtplib
import ssl
from email.message import EmailMessage


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def smtp_configured() -> bool:
    return bool(
        _env("SMTP_HOST")
        and _env("SMTP_USERNAME")
        and _env("SMTP_PASSWORD")
        and _env("SMTP_FROM_EMAIL")
    )


def send_password_reset_email(
    *,
    recipient: str,
    reset_url: str,
) -> bool:
    """
    Envia o link de recuperação sem registrar token ou URL em logs.
    Retorna False quando SMTP ainda não está configurado.
    """
    host = _env("SMTP_HOST")
    username = _env("SMTP_USERNAME")
    password = _env("SMTP_PASSWORD")
    from_email = _env("SMTP_FROM_EMAIL")
    from_name = _env("SMTP_FROM_NAME", "Printflow")
    port = int(_env("SMTP_PORT", "587") or "587")
    use_ssl = _env("SMTP_USE_SSL", "false").lower() in {"1", "true", "yes", "on"}

    if not (host and username and password and from_email):
        return False

    message = EmailMessage()
    message["Subject"] = "Redefinição de senha - Printflow"
    message["From"] = f"{from_name} <{from_email}>"
    message["To"] = recipient
    message.set_content(
        "Recebemos uma solicitação para redefinir sua senha no Printflow.\n\n"
        "Use o link abaixo em até 15 minutos:\n"
        f"{reset_url}\n\n"
        "Se você não solicitou esta alteração, ignore esta mensagem."
    )

    if use_ssl:
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(host, port, context=context, timeout=15) as smtp:
            smtp.login(username, password)
            smtp.send_message(message)
        return True

    with smtplib.SMTP(host, port, timeout=15) as smtp:
        smtp.ehlo()
        smtp.starttls(context=ssl.create_default_context())
        smtp.ehlo()
        smtp.login(username, password)
        smtp.send_message(message)

    return True
