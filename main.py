import os

from bot import TelegramBot
from dotenv import load_dotenv
from constants import CHATGPT_PROMPT

if __name__ == '__main__':
    load_dotenv()

    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    NOTION_TOKEN = os.getenv('NOTION_TOKEN')
    NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
    GOOGLE_SHEETS_CREDENTIALS_FILE = 'credentials.json'
    GOOGLE_SHEETS_ID = os.getenv('GOOGLE_SHEETS_ID')
    OPENAI_API_TOKEN = os.getenv('OPENAI_API_TOKEN')
    bot = TelegramBot(TELEGRAM_TOKEN, NOTION_TOKEN, NOTION_DATABASE_ID, GOOGLE_SHEETS_CREDENTIALS_FILE,
                      GOOGLE_SHEETS_ID, OPENAI_API_TOKEN)
    bot.application.run_polling()
