from js import Response
import os
import json
import asyncio
import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from bot import TelegramBot
from dotenv import load_dotenv
from constants import CHATGPT_PROMPT
from logger_client import LoggerClient
from notion_client import NotionClient

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
GOOGLE_SHEETS_CREDENTIALS_FILE = 'credentials.json'
GOOGLE_SHEETS_ID = os.getenv('GOOGLE_SHEETS_ID')
OPENAI_API_TOKEN = os.getenv('OPENAI_API_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
SECRET_TOKEN = os.getenv('SECRET_TOKEN')
TELEGRAM_USER_ID = os.getenv('TELEGRAM_USER_ID')
NOTION_USER_ID = os.getenv('NOTION_USER_ID')

bot = TelegramBot(TELEGRAM_TOKEN, NOTION_TOKEN, NOTION_DATABASE_ID, GOOGLE_SHEETS_CREDENTIALS_FILE,
                  GOOGLE_SHEETS_ID, OPENAI_API_TOKEN, WEBHOOK_URL, SECRET_TOKEN, NOTION_USER_ID, TELEGRAM_USER_ID)

application = bot.application

logger = LoggerClient('output/app_output.txt')


def on_fetch(request):
    return Response.new("Hello World!")

async def process_update(event):
    # update = event
    # event = e
    update = Update.de_json(event, application.bot)
    await bot.application.initialize()
    await bot.application.process_update(update)


def main(event=None):
    props = bot.notion_client.get_database_properties(NOTION_DATABASE_ID)
    logger.log_json(props)
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
