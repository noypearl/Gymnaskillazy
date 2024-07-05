import os
from bot import TelegramBot
from dotenv import load_dotenv

if __name__ == '__main__':
    load_dotenv()

    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    NOTION_TOKEN = os.getenv('NOTION_TOKEN')
    NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
    GOOGLE_SHEETS_CREDENTIALS_FILE = 'credentials.json'
    GOOGLE_SHEETS_ID = os.getenv('GOOGLE_SHEETS_ID')

    bot = TelegramBot(TELEGRAM_TOKEN, NOTION_TOKEN, NOTION_DATABASE_ID, GOOGLE_SHEETS_CREDENTIALS_FILE,
                      GOOGLE_SHEETS_ID)
    bot.application.run_polling()
