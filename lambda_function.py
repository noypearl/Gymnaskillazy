import json
import asyncio
import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
from bot import TelegramBot
from dotenv import load_dotenv
from constants import CHATGPT_PROMPT

load_dotenv()
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
GOOGLE_SHEETS_CREDENTIALS_FILE = 'credentials.json'
GOOGLE_SHEETS_ID = os.getenv('GOOGLE_SHEETS_ID')
OPENAI_API_TOKEN = os.getenv('OPENAI_API_TOKEN')
WEBHOOK_URL = os.getenv('WEBHOOK_URL')
SECRET_TOKEN = os.getenv('SECRET_TOKEN')
NOTION_USER_ID = os.getenv('NOTION_USER_ID')
TELEGRAM_USER_ID = os.getenv('TELEGRAM_USER_ID')

bot = TelegramBot(TELEGRAM_TOKEN, NOTION_TOKEN, NOTION_DATABASE_ID, GOOGLE_SHEETS_CREDENTIALS_FILE,
                  GOOGLE_SHEETS_ID, OPENAI_API_TOKEN, WEBHOOK_URL, SECRET_TOKEN, NOTION_USER_ID, TELEGRAM_USER_ID)
application = bot.application
bot.set_webhook()


async def process_update(event):
    # update = event
    # event = e
    update = Update.de_json(event, application.bot)
    await bot.application.initialize()
    await bot.application.process_update(update)


def lambda_handler(event, context):
    print("LOLZ")
    # e = {'update_id': 233648036, 'message': {'message_id': 1536, 'from': {'id': 856026537, 'is_bot': False, 'first_name': 'Noi', 'language_code': 'en'}, 'chat': {'id': 856026537, 'first_name': 'Noi', 'type': 'private'}, 'date': 1720299381, 'text': '/start', 'entities': [{'offset': 0, 'length': 6, 'type': 'bot_command'}]}}
    # event = e
    print(f"event: {event}")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(process_update(event))
    return {
        'statusCode': 200,
        'body': json.dumps('Succss')
    }

