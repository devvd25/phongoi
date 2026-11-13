import logging
import smtplib
from email.message import EmailMessage

from .config import settings

log = logging.getLogger(__name__)


def mail_enabled() -> bool:
    return bool(settings.smtp_host)


def send_mail(to: str, subject: str, body: str) -> bool:
    """Gửi email qua SMTP. Trả về False nếu chưa cấu hình SMTP (môi trường phát triển)."""
    if not mail_enabled():
        log.info("SMTP chưa cấu hình, bỏ qua email tới %s: %s", to, subject)
        return False
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = settings.smtp_from, to, subject
    msg.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as s:
        s.starttls()
        if settings.smtp_user:
            s.login(settings.smtp_user, settings.smtp_password)
        s.send_message(msg)
    return True
