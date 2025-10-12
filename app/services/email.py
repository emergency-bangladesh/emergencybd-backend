import email.utils
import smtplib
import ssl
import uuid
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Literal

from ..core.config import config


def send_email(
    mailto: str,
    subject: str,
    body: str,
    content_type: Literal["html", "plain"],
    cc: list[str] | None = None,
) -> None:
    message = MIMEMultipart()
    message.attach(MIMEText(body, content_type))
    message["From"] = config.smtp_mailfrom
    message["To"] = mailto
    message["Subject"] = subject
    message["Cc"] = ", ".join(cc) if cc else ""
    message["Reply-To"] = config.smtp_mailfrom
    message["Message-ID"] = f"<{uuid.uuid4()}@{config.smtp_server}>"
    message["Date"] = email.utils.formatdate(localtime=True)

    is_ssl = config.smtp_port == 465
    server = (
        smtplib.SMTP_SSL(
            config.smtp_server,
            config.smtp_port,
            context=ssl.create_default_context(),
        )
        if is_ssl
        else smtplib.SMTP(config.smtp_server, config.smtp_port)
    )
    if not is_ssl:
        server.starttls(context=ssl.create_default_context())

    server.login(config.smtp_mailfrom, config.smtp_mailfrom_password)
    server.sendmail(
        config.smtp_mailfrom,
        list(set([mailto] + (cc or []))),
        message.as_string(),
    )

    server.quit()

    print(f"Email sent to {mailto} with CC: {cc} successfully!")
