import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from google_sheets_client import GoogleSheetsClient
from notion_client import NotionClient
from constants import EXPLANATIONS_TEXT, MULTI_TAGS

class TelegramBot:
    CHOOSING_TYPE, CHOOSING_COACH, COLLECTING_DESCRIPTIONS, ADDING_CUSTOM_EXERCISE, ADDING_CUSTOM_DESCRIPTION = range(5)

    def __init__(self, telegram_token, notion_token, notion_database_id, google_sheets_credentials_file, google_sheets_id):
        self.telegram_token = telegram_token
        self.google_sheets_client = GoogleSheetsClient(google_sheets_credentials_file, google_sheets_id)
        self.notion_client = NotionClient(notion_token, notion_database_id)
        self.sessions = {}

        # Configure logging
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        self.application = Application.builder().token(self.telegram_token).build()

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.new_log)],
            states={
                self.CHOOSING_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.choose_type)],
                self.CHOOSING_COACH: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.choose_coach)],
                self.COLLECTING_DESCRIPTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_description)],
                self.ADDING_CUSTOM_EXERCISE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_custom_exercise)],
                self.ADDING_CUSTOM_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_custom_description)]
            },
            fallbacks=[CommandHandler('stop', self.stop)],
        )

        self.application.add_handler(conv_handler)
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("stop", self.stop))
        self.application.add_handler(CommandHandler("status", self.view_status))

    async def start(self, update: Update, context: CallbackContext) -> None:
        await update.message.reply_text('Welcome! Use /start to start logging a new lesson.')

    async def view_status(self, update: Update, context: CallbackContext) -> None:
        user_id = update.message.from_user.id
        if user_id not in self.sessions:
            await update.message.reply_text("No active session found. Use /start to begin logging a new lesson.")
            return

        log_data = self.sessions[user_id]
        status_message = f"Current log data:\n\nType: {log_data['type'].capitalize()}\nCoach: {log_data['coach']}\nExercises:\n"

        for idx, exercise in enumerate(log_data['exercises']):
            status_message += f"{idx + 1}. {exercise['type']} - {exercise['description']}\n"

        if 'custom_exercises' in log_data:
            status_message += "\nCustom Exercises:\n"
            for idx, exercise in enumerate(log_data['custom_exercises']):
                status_message += f"{idx + 1}. {exercise['type']} - {exercise['description']}\n"

        await update.message.reply_text(status_message)

    async def new_log(self, update: Update, context: CallbackContext) -> int:
        user_id = update.message.from_user.id
        self.logger.info(f"User ID: {user_id}")
        self.sessions[user_id] = {'exercises': []}
        await update.message.reply_text('Is it a "Strength" or "Skill" lesson?',
                                        reply_markup=ReplyKeyboardMarkup([['Strength', 'Skill']], one_time_keyboard=True))
        return self.CHOOSING_TYPE

    async def choose_type(self, update: Update, context: CallbackContext) -> int:
        user_id = update.message.from_user.id
        lesson_type = update.message.text.lower()
        self.sessions[user_id]['type'] = lesson_type
        await update.message.reply_text('Who is the coach? Choose from: Shahar, Alon, Sagi, Yair',
                                        reply_markup=ReplyKeyboardMarkup([['Shahar', 'Alon', 'Sagi', 'Yair']], one_time_keyboard=True))
        return self.CHOOSING_COACH

    async def choose_coach(self, update: Update, context: CallbackContext) -> int:
        user_id = update.message.from_user.id
        coach = update.message.text
        self.sessions[user_id]['coach'] = coach
        sheet = self.google_sheets_client.get_current_sheet()
        exercise_data = []
        if self.sessions[user_id]['type'] == 'strength':
            exercise_data = sheet.col_values(1)[1:10]  # Column A
        else:
            exercise_data = sheet.col_values(2)[1:10]  # Column B

        self.sessions[user_id]['exercises'] = [{'type': ex, 'description': ''} for ex in exercise_data]
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Starting {self.sessions[user_id]['type']} lesson with {coach}. Let's start with the exercises.")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{self.sessions[user_id]['exercises'][0]['type']} - talk to me.")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=EXPLANATIONS_TEXT)
        return self.COLLECTING_DESCRIPTIONS

    async def add_custom_exercise(self, update: Update, context: CallbackContext) -> int:
        user_id = update.message.from_user.id
        custom_exercise_title = update.message.text
        self.sessions[user_id]['custom_exercise_title'] = custom_exercise_title
        await context.bot.send_message(chat_id=update.effective_chat.id, text='Enter the custom exercise description:')
        return self.ADDING_CUSTOM_DESCRIPTION

    async def add_custom_description(self, update: Update, context: CallbackContext) -> int:
        user_id = update.message.from_user.id
        custom_exercise_description = update.message.text
        custom_exercise = {
            'type': self.sessions[user_id]['custom_exercise_title'],
            'description': custom_exercise_description
        }
        if 'custom_exercises' not in self.sessions[user_id]:
            self.sessions[user_id]['custom_exercises'] = []
        self.sessions[user_id]['custom_exercises'].append(custom_exercise)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text='Custom exercise was added '
                                            'successfully.')
        if 'current_exercise' not in self.sessions[user_id]:
            self.sessions[user_id]['current_exercise'] = 0
        current_exercise = self.sessions[user_id]['current_exercise']
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{self.sessions[user_id]['exercises'][current_exercise]['type']} exercise - talk to me")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=EXPLANATIONS_TEXT)
        return self.COLLECTING_DESCRIPTIONS

    async def collect_description(self, update: Update, context: CallbackContext) -> int:
        user_id = update.message.from_user.id
        description = update.message.text
        if description.lower() == "end":
            await update.message.reply_text('Updating...')
            page_id = await self.notion_client.save_to_notion(user_id,
                                                              self.sessions)
            await self.notion_client.append_block_to_page(page_id, self.sessions[user_id])
            await self.notify_lesson_logged(update, user_id)
            return ConversationHandler.END

        elif description.lower() == "skip":
            await self.skip_exercise(update, user_id)
            return self.COLLECTING_DESCRIPTIONS

        elif description.lower() == "add":
            await context.bot.send_message(chat_id=update.effective_chat.id, text='Enter the custom exercise title:')
            return self.ADDING_CUSTOM_EXERCISE

        else:
            await self.add_description(update, user_id, description)
            return self.COLLECTING_DESCRIPTIONS

    async def notify_lesson_logged(self, update: Update, user_id):
        log_data = self.sessions[user_id]
        status_message = (f"Lesson completed! NOICE!! \n"
                          f"You had a {log_data['type'].capitalize()} lesson with {log_data['coach']}!\n"
                          f"And did :\n")

        for idx, exercise in enumerate(log_data['exercises']):
            if exercise['description']:
                status_message += f"{idx + 1}. {exercise['type']} - {exercise['description']}\n"

        if 'custom_exercises' in log_data:
            status_message += "\nCustom Exercises:\n"
            for idx, exercise in enumerate(log_data['custom_exercises']):
                if exercise['description']:
                    status_message += f"{idx + 1}. {exercise['type']} - {exercise['description']}\n"

        await update.message.reply_text(status_message)
        await update.message.reply_text('Lesson data added to Notion successfully!')

    async def skip_exercise(self, update: Update, user_id):
        if 'current_exercise' not in self.sessions[user_id]:
            self.sessions[user_id]['current_exercise'] = 0
        current_exercise = self.sessions[user_id]['current_exercise']
        current_exercise += 1
        if current_exercise == len(self.sessions[user_id]['exercises']):
            self.sessions[user_id]['current_exercise'] = current_exercise
            await update.message.reply_text('exercise was skipped.')
            await update.message.reply_text('All exercises collected. Type "end" to finish and save to Notion.')
        else:
            self.sessions[user_id]['current_exercise'] = current_exercise
            await update.message.reply_text(f"{self.sessions[user_id]['exercises'][current_exercise]['type']} - talk to me.")
            await update.message.reply_text(EXPLANATIONS_TEXT)

    async def add_description(self, update: Update, user_id, description):
        if 'current_exercise' not in self.sessions[user_id]:
            self.sessions[user_id]['current_exercise'] = 0
        current_exercise = self.sessions[user_id]['current_exercise']
        self.sessions[user_id]['exercises'][current_exercise]['description'] = description
        current_exercise += 1
        if current_exercise < len(self.sessions[user_id]['exercises']):
            self.sessions[user_id]['current_exercise'] = current_exercise
            await update.message.reply_text(f"{self.sessions[user_id]['exercises'][current_exercise]['type']} exercise - talk to me")
        else:
            await update.message.reply_text("All exercises collected.\nType 'end' to finish and save to Notion \nor 'add' - to add a custom exercise")

    async def stop(self, update: Update, context: CallbackContext) -> int:
        user_id = update.message.from_user.id
        if user_id in self.sessions:
            del self.sessions[user_id]
        await update.message.reply_text('Stopped the logging of the lesson.')
        return ConversationHandler.END

    def run(self):
        self.application.run_polling()

if __name__ == '__main__':
    from dotenv import load_dotenv
    import os

    load_dotenv()

    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
    NOTION_TOKEN = os.getenv('NOTION_TOKEN')
    NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
    GOOGLE_SHEETS_CREDENTIALS_FILE = 'credentials.json'
    GOOGLE_SHEETS_ID = os.getenv('GOOGLE_SHEETS_ID')

    bot = TelegramBot(
        TELEGRAM_TOKEN,
        NOTION_TOKEN,
        NOTION_DATABASE_ID,
        GOOGLE_SHEETS_CREDENTIALS_FILE,
        GOOGLE_SHEETS_ID
    )
    bot.run()
