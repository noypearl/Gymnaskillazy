import asyncio
import json
import os

from dotenv import load_dotenv
from telegram import Update

from bot import TelegramBot
from logger_client import LoggerClient

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
GOOGLE_SHEETS_CREDENTIALS_FILE = 'credentials.json'
GOOGLE_SHEETS_MAIN_DOC_ID = os.getenv('GOOGLE_SHEETS_MAIN_DOC_ID')
GOOGLE_SHEETS_USER_TEMPLATE_DOC_ID = os.getenv('GOOGLE_SHEETS_USER_TEMPLATE_DOC_ID')
GOOGLE_SHEETS_USER_LOG_FOLDER_ID = os.getenv('GOOGLE_SHEETS_USER_LOG_FOLDER_ID')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
SECRET_TOKEN = os.getenv('SECRET_TOKEN')
TELEGRAM_USER_ID = os.getenv('TELEGRAM_USER_ID')

bot = TelegramBot(
    telegram_token=TELEGRAM_TOKEN,
    google_sheets_credentials_file=GOOGLE_SHEETS_CREDENTIALS_FILE,
    google_main_sheet_doc_id=GOOGLE_SHEETS_MAIN_DOC_ID,
    google_user_template_doc_id=GOOGLE_SHEETS_USER_TEMPLATE_DOC_ID,
    google_user_log_folder_id=GOOGLE_SHEETS_USER_LOG_FOLDER_ID,
    webhook_url=WEBHOOK_URL,
    secret_token=SECRET_TOKEN,
    telegram_user_id=TELEGRAM_USER_ID
)

application = bot.application

logger = LoggerClient('output/app_output.txt')


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
