#!/usr/bin/env python
# pylint: disable=unused-argument
# This program is dedicated to the public domain under the CC0 license.

"""Simple inline keyboard bot with multiple CallbackQueryHandlers.

This Bot uses the Application class to handle the bot.
First, a few callback functions are defined as callback query handler. Then, those functions are
passed to the Application and registered at their respective places.
Then, the bot is started and runs until we press Ctrl-C on the command line.
Usage:
Example of a bot that uses inline keyboard that has multiple CallbackQueryHandlers arranged in a
ConversationHandler.
Send /start to initiate the conversation.
Press Ctrl-C on the command line to stop the bot.
"""
import asyncio
import json
import locale
import logging
import os

import redis.asyncio as redis
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
)

from database.database import Session
from database.models import Category, Transaction

locale.setlocale(locale.LC_TIME, 'ru_RU.UTF-8')

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
# set higher logging level for httpx to avoid all GET and POST requests being logged
logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)



async def edit_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    transaction_id = query.data.split('_')[1]
    with Session() as session:
        transaction = session.get(Transaction, transaction_id)
        if not transaction:
            await query.edit_message_text(text="Transaction not found")
            return ConversationHandler.END


async def remove_transaction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    transaction_id = int(query.data.split('_')[1])
    with Session() as session:
        transaction = session.get(Transaction, transaction_id)
        if not transaction:
            await query.edit_message_text(text="Транзакция не найдена")
            return
        session.delete(transaction)
        session.commit()
        await query.edit_message_text(text="Транзакция удалена")
        return


async def redis_command_listener(application):
    logger.info("Starting redis command listener")
    redis_url = os.getenv('REDIS_ADDR')
    redis_client = redis.from_url(redis_url, decode_responses=True)

    while True:
        command = await redis_client.rpop('transactions')
        if not command:
            await asyncio.sleep(1)
            continue
        try:
            command = json.loads(command)
            user_id = int(os.getenv('BOT_ADMIN_ID'))

            with Session() as session:
                category = session.query(Category).filter(Category.name == command['category']).first()

                transaction = Transaction(
                    place=command['place'],
                    receipt_date=command['receipt_date'],
                    mail_date=command.get('mail_date'),
                    total=command['total'],
                    category=category,
                )
                session.add(transaction)
                session.commit()

                transaction_id = transaction.transaction_id

                reply_text = (
                    f"*Добавлена транзакция*\n"
                    f"*Отправитель*: {transaction.place}\n"
                    f"*Дата*: {transaction.receipt_date.strftime('%d %B %Y, %H:%M')}\n"
                    f"*Сумма*: {transaction.total:.2f} ₽\n"
                    f"*Категория*: {transaction.category.name}"
                )

            keyboard = [[
                InlineKeyboardButton("Edit", callback_data=f"edit_{transaction_id}"),
                InlineKeyboardButton("Remove", callback_data=f"remove_{transaction_id}"),
            ]]

            reply_markup = InlineKeyboardMarkup(keyboard)

            await application.bot.send_message(chat_id=user_id,
                                               text=reply_text,
                                               reply_markup=reply_markup,
                                               parse_mode='MarkdownV2')

        except ValueError as e:
            logger.exception('Error processing transaction', exc_info=e)


async def on_startup(application):
    application.create_task(redis_command_listener(application))


def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(os.getenv('BOT_TOKEN')).post_init(on_startup).build()

    # Handle remove transaction
    application.add_handler(CallbackQueryHandler(remove_transaction, pattern="remove_.*"))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
