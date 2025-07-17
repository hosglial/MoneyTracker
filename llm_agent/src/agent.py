import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from zoneinfo import ZoneInfo

import httpx
import redis.asyncio as redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


REDIS_URL = os.getenv('REDIS_ADDR')
HTTP_ENDPOINT = 'https://openrouter.ai/api/v1/chat/completions'

system_prompt = '''
Ты — помощник для автоматизации учёта расходов.
Тебе дан текст кассового чека.
Твоя задача — извлечь из него следующие данные:
Категорию чека (Выбирай СТРОГО из следующих категорий: 
Продукты,
Еда вне дома,
Здоровье,
Транспорт,
Одежда и обувь,
Товары для дома,
Развлечения,
Подарки,
Техника,
Отдых,
Сигареты,
Красота,
Другое
)
Общую сумму чека (только число, без валюты и лишних символов).
Время и дата покупки (в формате ISO 8601,  например: 2024-06-12T15:30:00).
Отправителя чека (обычно это организация, ООО, ИП и т.п.)
Ответь строго в формате JSON:
{
"category": "<категория>",
"total": <сумма>,
"date": "<время и дата покупки>",
"place": "<отправитель чека>"
}
Текст чека:
'''


async def send_to_llm(mail_data: dict, http_client: httpx.AsyncClient):
    request_body = {
        "model": "openai/gpt-4.1-nano",
        "messages": [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": system_prompt + mail_data["plain_text"]
                    },
                ]
            }
        ],

    }

    request_headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"
    }
    response = await http_client.post(url=HTTP_ENDPOINT, json=request_body, headers=request_headers)
    response.raise_for_status()
    return response


async def process_queue():
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    async with httpx.AsyncClient() as http_client:
        while True:
            msg_raw = await redis_client.rpop('mail_queue')
            if msg_raw is None:
                await asyncio.sleep(1)
                continue

            msg_data = json.loads(msg_raw)
            logger.info(f"Got item from queue: {msg_data}")
            try:
                response = await send_to_llm(msg_data, http_client)
            except HTTPError as e:
                logger.error(f"Failed to send HTTP request: {e}")
                continue

            llm_response = json.loads(response.json()['choices'][0]['message']['content'])
            logger.info(f"Sent to LLM, status: {response.status_code}, response: {llm_response}")
            msg_data.update(llm_response)

            if msg_data['receipt_date']:
                dt = datetime.fromisoformat(msg_data['receipt_date'])
                # TODO: get timezone or offsetfrom msg_data['timezone']
                tz = ZoneInfo('Europe/Moscow')
                dt_with_tz = dt.astimezone(tz)
                msg_data['receipt_date'] = dt_with_tz.isoformat()

            await redis_client.lpush('transactions', json.dumps(msg_data, ensure_ascii=False))


if __name__ == '__main__':
    logger.info("LLM agent started")
    asyncio.run(process_queue())
