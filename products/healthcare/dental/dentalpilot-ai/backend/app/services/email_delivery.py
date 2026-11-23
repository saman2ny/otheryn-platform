import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

from app.core.config import settings


class EmailDeliveryError(RuntimeError):
    pass


def send_email(
    outbox_id: str,
    recipient: str,
    subject: str,
    body_text: str,
) -> None:
    if not settings.smtp_host or not settings.smtp_sender_email:
        raise EmailDeliveryError("SMTP_HOST and SMTP_SENDER_EMAIL must be configured.")
    if settings.smtp_use_ssl and settings.smtp_use_starttls:
        raise EmailDeliveryError("Choose implicit TLS or STARTTLS, not both.")
    if (settings.smtp_username and not settings.smtp_password) or (
        settings.smtp_password and not settings.smtp_username
    ):
        raise EmailDeliveryError("SMTP username and password must be configured together.")
    if "\r" in subject or "\n" in subject:
        raise EmailDeliveryError("Email subject contains invalid line breaks.")

    message = EmailMessage()
    message["From"] = formataddr((settings.smtp_sender_name, settings.smtp_sender_email))
    message["To"] = recipient
    message["Subject"] = subject
    message["Message-ID"] = make_msgid(id_string=outbox_id, domain="dentalpilot.local")
    message.set_content(body_text)
    context = ssl.create_default_context()

    try:
        if settings.smtp_use_ssl:
            with smtplib.SMTP_SSL(
                settings.smtp_host,
                settings.smtp_port,
                timeout=20,
                context=context,
            ) as client:
                _authenticate(client)
                client.send_message(message)
        else:
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as client:
                if settings.smtp_use_starttls:
                    client.starttls(context=context)
                _authenticate(client)
                client.send_message(message)
    except (smtplib.SMTPException, OSError) as exc:
        raise EmailDeliveryError("SMTP delivery failed; the message will be retried.") from exc


def _authenticate(client: smtplib.SMTP) -> None:
    if settings.smtp_username and settings.smtp_password:
        client.login(settings.smtp_username, settings.smtp_password)
