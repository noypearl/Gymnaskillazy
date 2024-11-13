import asyncio
import json
import os

from dotenv import load_dotenv
from telegram import Update

from bot import TelegramBot
from utilities.config import (SECRET_TOKEN, TELEGRAM_TOKEN, TELEGRAM_USER_ID,
                              WEBHOOK_URL)
from utilities.logger_client import LoggerClient

logger = LoggerClient('output/app_output.txt')



bot = TelegramBot(
    telegram_token=TELEGRAM_TOKEN,
    webhook_url=WEBHOOK_URL,
    secret_token=SECRET_TOKEN,
    telegram_user_id=TELEGRAM_USER_ID,
    logger=logger
)

application = bot.application



async def process_update(event):
    # update = event
    # event = e
    update = Update.de_json(event, application.bot)
    await bot.application.initialize()
    await bot.application.process_update(update)


def main(event=None):
    if event is None:
        # Polling mode
        print("No event - running the app in Telegram Polling mode (no "
              "webhook)")
        application.run_polling()
    else:
        # Webhook mode
        loop = asyncio.get_event_loop()
        loop.run_until_complete(process_update(event))
        return {
            'statusCode': 200,
            'body': json.dumps('Success')
        }

if __name__ == '__main__':
    main()
