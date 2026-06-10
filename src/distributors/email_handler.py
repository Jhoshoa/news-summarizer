import asyncio
import smtplib
from email.message import EmailMessage
from email.utils import formataddr

from loguru import logger


class EmailHandler:
    """Envia briefs por SMTP."""

    def __init__(self, db_repository=None, settings=None):
        self.db = db_repository
        self.settings = settings

        if self.is_configured:
            logger.info("Email handler inicializado con SMTP")
        else:
            logger.info("Email handler inicializado sin SMTP (modo desarrollo)")

    @property
    def is_configured(self) -> bool:
        if not self.settings or not getattr(self.settings, "email_enabled", False):
            return False
        required = (
            getattr(self.settings, "smtp_host", None),
            getattr(self.settings, "smtp_port", None),
            getattr(self.settings, "smtp_username", None),
            getattr(self.settings, "smtp_password", None),
            getattr(self.settings, "smtp_from_email", None),
        )
        return all(required)

    async def send_message(self, to_email: str, subject: str, body: str) -> bool:
        """Envia un correo en texto plano."""

        if not self.is_configured:
            logger.warning(f"SMTP no configurado. Mensaje no enviado a {to_email}: {subject}")
            return False

        message = self._build_message(to_email, subject, body)
        try:
            await asyncio.to_thread(self._send_sync, message)
            logger.info(f"Email enviado a {to_email}")
            return True
        except Exception as exc:
            logger.error(f"Error enviando email a {to_email}: {exc}")
            return False

    def _build_message(self, to_email: str, subject: str, body: str) -> EmailMessage:
        from_email = self.settings.smtp_from_email
        from_name = self.settings.smtp_from_name

        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = formataddr((from_name, from_email))
        message["To"] = to_email
        message.set_content(body)
        return message

    def _send_sync(self, message: EmailMessage) -> None:
        host = self.settings.smtp_host
        port = int(self.settings.smtp_port)
        username = self.settings.smtp_username
        password = self.settings.smtp_password

        with smtplib.SMTP(host, port, timeout=20) as smtp:
            smtp.starttls()
            smtp.login(username, password)
            smtp.send_message(message)
