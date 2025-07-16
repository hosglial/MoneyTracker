import imaplib
import os
from dotenv import load_dotenv
import logging
from mail_services import EmailData, extract_email_fields, fetch_email, get_last_email_bytes
import redis

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

load_dotenv(dotenv_path=os.getenv('CONFIG_PATH') + '/.env')

PASSWORD = os.getenv('YANDEX_PASS')
REDIS_URL = os.getenv('REDIS_ADDR')

if not PASSWORD:
    raise ValueError("YANDEX_PASS is not set")


def push_email_to_queue(redis_client: redis.Redis, email_data: EmailData):
    redis_client.lpush('mail_queue', email_data.model_dump_json())
    logger.info(f"Pushed email to queue: {email_data.subject}")


if __name__ == '__main__':
    mail = imaplib.IMAP4_SSL('imap.yandex.ru')
    result = mail.login('hosglial', PASSWORD)
    logger.info(f"Login result: {result[0]}")
    
    redis_client = redis.from_url(REDIS_URL)

    try:
        mail.select('Receipts')
        # email_bytes = get_last_email_bytes(mail)
        # email_data = extract_email_fields(email_bytes)
        
        while True:
            email_data = fetch_email(mail)
            logger.info(f"Email text: {email_data.subject}")
            push_email_to_queue(redis_client, email_data)


    except KeyboardInterrupt:
        mail.logout()

