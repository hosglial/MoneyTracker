import imaplib
import os
import logging
import time
from mail_services import EmailData, extract_email_fields, fetch_email, get_last_email_bytes
import redis

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


PASSWORD = os.getenv('YANDEX_PASS')
REDIS_URL = os.getenv('REDIS_ADDR')

if not PASSWORD:
    raise ValueError("YANDEX_PASS is not set")


def push_email_to_queue(redis_client: redis.Redis, email_data: EmailData):
    redis_client.lpush('mail_queue', email_data.model_dump_json())
    logger.info(f"Pushed email to queue: {email_data.subject} {email_data.sender}")


def connect_imap():
    """Создает новое IMAP соединение"""
    mail = imaplib.IMAP4_SSL('imap.yandex.ru')
    result = mail.login('hosglial', PASSWORD)
    logger.info(f"Login result: {result[0]}")
    mail.select('Receipts')
    return mail


if __name__ == '__main__':
    redis_client = redis.from_url(REDIS_URL)
    mail = None

    while True:
        try:
            # Подключаемся к IMAP
            if mail is None:
                mail = connect_imap()
            
            # Получаем письмо
            email_data = fetch_email(mail)
            logger.info(f"Email subject: {email_data.subject}")
            push_email_to_queue(redis_client, email_data)

        except (BrokenPipeError, ConnectionResetError, OSError) as e:
            logger.error(f"Connection error: {e}")
            logger.info("Reconnecting to IMAP server...")
            try:
                if mail:
                    mail.logout()
            except:
                pass
            mail = None
            time.sleep(5)  # Ждем 5 секунд перед переподключением
            
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            if mail:
                mail.logout()
            break
            
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            time.sleep(1)

