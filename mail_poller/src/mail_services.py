import email
import logging
import re
from datetime import datetime
from email.header import decode_header

from bs4 import BeautifulSoup
from pydantic import BaseModel, field_serializer, field_validator, computed_field

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def html_to_text(html):
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n", strip=True)


class EmailData(BaseModel):
    sender: str
    reciever: str
    subject: str
    mail_date: datetime | None = None
    message_id: str
    plain_text: str

    @field_validator('sender', 'reciever', 'subject')
    def validate_email_fields(cls, v):
        if not v:
            return ""
        decoded_parts = decode_header(v)
        return ''.join(
            part.decode(charset or 'utf-8') if isinstance(part, bytes) else part
            for part, charset in decoded_parts
        )

    @field_validator('mail_date', mode='before')
    def validate_date(cls, v):
        if not v:
            return None
        # Date format: Mon, 07 Jul 2025 18:54:36 +0300 (MSK)
        # Remove timezone info via regexand parse
        try:
            return datetime.strptime(re.sub(r' \(\w+\)$', '', v), '%a, %d %b %Y %H:%M:%S %z')
        except ValueError:
            return None

    @field_serializer('mail_date')
    def serialize_date(self, value):
        if value is None:
            return None
        return value.isoformat()

    @computed_field
    def timezone(self) -> str:
        if self.mail_date is None:
            return 'UTC+3'
        return self.mail_date.tzname()


def extract_html_from_email(raw_email_bytes):
    msg = email.message_from_bytes(raw_email_bytes)
    for part in msg.walk():
        if part.get_content_type() == "text/html":
            payload = part.get_payload(decode=True)
            charset = part.get_content_charset() or 'utf-8'
            return payload.decode(charset)
    return None


def extract_email_fields(raw_email_bytes: bytes) -> EmailData:
    msg = email.message_from_bytes(raw_email_bytes)
    html_body = extract_html_from_email(raw_email_bytes)
    if html_body:
        text = html_to_text(html_body)
    # Извлекаем ключевые поля
    return EmailData(
        sender=msg.get('From'),
        reciever=msg.get('To'),
        subject=msg.get('Subject'),
        mail_date=msg.get('Date'),
        message_id=msg.get('Message-ID'),
        plain_text=text,
    )

def get_last_email_bytes(mail) -> bytes | None:
    """
    Получить последнее письмо из IMAP-ящика как bytes.
    :param mail: объект imaplib.IMAP4_SSL
    :return: bytes или None
    """
    result, messages = mail.search(None, 'ALL')
    if result != 'OK' or not messages or not messages[0]:
        return None
    latest_email_id = messages[0].split()[-1]
    result, msg_data = mail.fetch(latest_email_id, '(RFC822)')
    if result != 'OK' or not msg_data:
        return None
    for part in msg_data:
        if isinstance(part[0], bytes) and part[0].find(b'RFC822') != -1:
            return part[1]
    return None

def fetch_email(mail):
    tag = mail._new_tag().decode()
    mail.send(f'{tag} IDLE\r\n'.encode())
    while True:
        resp = mail.readline()
        if b'EXISTS' in resp:
            # Получаем последнее письмо
            msg_data = get_last_email_bytes(mail)
            email_data = extract_email_fields(msg_data)
            return email_data
