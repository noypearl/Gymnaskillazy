import json
import logging
from openai import OpenAI
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from telegram.constants import ParseMode
from google_sheets_client import GoogleSheetsClient
from notion_client import NotionClient
from constants import EXPLANATIONS_TEXT, TELEGRAM_USER_ID, CHATGPT_PROMPT


class TelegramBot:
    CHOOSING_TYPE, CHOOSING_COACH, COLLECTING_DESCRIPTIONS, ADDING_CUSTOM_EXERCISE, ADDING_CUSTOM_DESCRIPTION, ASKING_ADDITIONAL_QUESTIONS, COLLECTING_ADDITIONAL_INFO = range(
        7)

    def __init__(self, telegram_token, notion_token, notion_database_id,
                 google_sheets_credentials_file, google_sheets_id,
                 openapi_token, webhook_url, secret_token):
        self.telegram_token = telegram_token
        self.openapi_token = openapi_token
        self.google_sheets_client = GoogleSheetsClient(google_sheets_credentials_file, google_sheets_id)
        self.notion_client = NotionClient(notion_token, notion_database_id)
        self.sessions = {}
        self.secret_token = secret_token
        self.webhook_url = webhook_url

        # Configure logging
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

        self.application = Application.builder().token(self.telegram_token).build()

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.new_log)],
            states={
                self.CHOOSING_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.choose_type)],
                self.CHOOSING_COACH: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.choose_coach)],
                self.COLLECTING_DESCRIPTIONS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_description)],
                self.ADDING_CUSTOM_EXERCISE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.add_custom_exercise)],
                self.ADDING_CUSTOM_DESCRIPTION: [MessageHandler(filters.TEXT
                                                                & ~filters.COMMAND, self.add_custom_description)],
                self.ASKING_ADDITIONAL_QUESTIONS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.ask_additional_questions)],
                self.COLLECTING_ADDITIONAL_INFO: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_additional_info)]
            },
            fallbacks=[CommandHandler('stop', self.stop)],
        )

        self.application.add_handler(conv_handler)
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("stop", self.stop))
        self.application.add_handler(CommandHandler("status", self.view_status))

    async def start(self, update: Update, context: CallbackContext) -> None:
        user_id = update.message.from_user.id
        print(f" USER ID: {user_id}")
        if user_id != TELEGRAM_USER_ID:
            await update.message.reply_text("Access denied. You are not authorized to use this bot.")
            return
        await update.message.reply_text('Welcome! Use /start to start '
                                        'logging a new lesson. 💪')

    async def ask_additional_questions(self, update: Update, context: CallbackContext) -> int:
        user_id = update.message.from_user.id
        self.additional_questions = self.google_sheets_client.get_additional_questions()
        self.current_question_index = 0
        self.sessions[user_id]['additional_info'] = []

        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"Additional Question: {self.additional_questions[self.current_question_index]}")
        return self.COLLECTING_ADDITIONAL_INFO

    async def collect_additional_info(self, update: Update, context: CallbackContext) -> int:
        user_id = update.message.from_user.id
        answer = update.message.text
        question = self.additional_questions[self.current_question_index]

        self.sessions[user_id]['additional_info'].append({'question': question, 'answer': answer})

        self.current_question_index += 1

        if self.current_question_index < len(self.additional_questions):
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=f"Additional Question: {self.additional_questions[self.current_question_index]}")
            return self.COLLECTING_ADDITIONAL_INFO
        else:
            await update.message.reply_text('Hurray! Got all the data!')
            await update.message.reply_text('Now using 🤖 AI 🤖 tricks to '
                                            'generate a nice title...')
            client = OpenAI(api_key=self.openapi_token)
            response = client.chat.completions.create(
                model="gpt-4",  # Use "gpt-4" for chat-based model
                messages=[
                    {"role": "system", "content": CHATGPT_PROMPT},
                    {"role": "user", "content": str(self.sessions)}
                ],
                max_tokens=30,
                n=1,
                stop=None,
                temperature=0.7
            )
            new_title = response.choices[0].message.content
            print(f"AI Generated a new title {new_title}")
            self.sessions[user_id]['title'] = new_title
            page_id = await self.notion_client.save_to_notion(user_id, new_title,
                                                              self.lesson_index, self.sessions)
            print(f"AI Generated a new title 2 {new_title}")
            await self.notion_client.append_block_to_page(page_id, self.sessions[user_id])
            await self.notify_lesson_logged(update, user_id)
            return ConversationHandler.END

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
        print(f"User ID: {user_id}")
        self.sessions[user_id] = {'exercises': []}
        self.lesson_index = self.google_sheets_client.get_new_lesson_index()
        await update.message.reply_text('Is it a "Strength" or "Skill" lesson?',
                                        reply_markup=ReplyKeyboardMarkup([['Strength', 'Skill']],
                                                                         one_time_keyboard=True))
        return self.CHOOSING_TYPE

    async def choose_type(self, update: Update, context: CallbackContext) -> int:
        user_id = update.message.from_user.id
        lesson_type = update.message.text.lower()
        self.sessions[user_id]['type'] = lesson_type
        await update.message.reply_text('Who is the coach? Choose from: Shahar, Alon, Sagi, Yair',
                                        reply_markup=ReplyKeyboardMarkup([['Shahar', 'Alon', 'Sagi', 'Yair']],
                                                                         one_time_keyboard=True))
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
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"Starting {self.sessions[user_id]['type']} lesson with {coach}. Let's start with the exercises.")
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"{self.sessions[user_id]['exercises'][0]['type']} - talk to me.")
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
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"{self.sessions[user_id]['exercises'][current_exercise]['type']} exercise - talk to me")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=EXPLANATIONS_TEXT)
        return self.COLLECTING_DESCRIPTIONS

    async def collect_description(self, update: Update, context: CallbackContext) -> int:
        user_id = update.message.from_user.id
        description = update.message.text
        if description.lower() == "end":

            await update.message.reply_text("All exercises were collected. "
                                            "Now, "
                                            "let's answer a few additional "
                                            "questions.")
            return await self.ask_additional_questions(update, context)

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
        print("in notify_lesson_logged")
        log_data = self.sessions[user_id]
        status_message = (f"⭐  Lesson completed \\! Noice\\!  ⭐ \n"
                          f"You had a *{log_data['type'].capitalize()}* lesson with *{log_data['coach']}*\n"
                          f"And did the following \\- \n\n")

        for idx, exercise in enumerate(log_data['exercises']):
            if exercise['description']:
                status_message += f"{idx + 1}\\. {exercise['type']}\\- {exercise['description']}\n"
        if 'custom_exercises' in log_data:
            status_message += "\n\nCustom Exercises:\n"
            for idx, exercise in enumerate(log_data['custom_exercises']):
                if exercise['description']:
                    status_message += f"{idx + 1}\\. {exercise['type']} \\- {exercise['description']}\n"
            status_message += "\n"

        status_message += '\n'
        if 'additional_info' in log_data:
            for item in log_data['additional_info']:
                status_message += f"*{item['question']}*: {item['answer']}\n"
        print("HELLO")
        await update.message.reply_text(status_message, parse_mode=ParseMode.MARKDOWN_V2)
        await update.message.reply_text(f"A whole lesson is added to Notion: \n"
                                        f"{self.sessions[user_id]['title']}")

    async def skip_exercise(self, update: Update, user_id):
        if 'current_exercise' not in self.sessions[user_id]:
            self.sessions[user_id]['current_exercise'] = 0
        current_exercise = self.sessions[user_id]['current_exercise']
        current_exercise += 1
        if current_exercise == len(self.sessions[user_id]['exercises']):
            self.sessions[user_id]['current_exercise'] = current_exercise
            await update.message.reply_text('exercise was skipped\.')
            await update.message.reply_text('🤸 All exercises collected🤸 \nType '
                                            '"end" to move to additional '
                                            'questions and save to Notion\nOr "add" - to add a custom exercise')
        else:
            self.sessions[user_id]['current_exercise'] = current_exercise
            await update.message.reply_text(EXPLANATIONS_TEXT)
            await update.message.reply_text(
                f"{self.sessions[user_id]['exercises'][current_exercise]['type']} - talk to me.")

    async def add_description(self, update: Update, user_id, description):
        if 'current_exercise' not in self.sessions[user_id]:
            self.sessions[user_id]['current_exercise'] = 0
        current_exercise = self.sessions[user_id]['current_exercise']
        self.sessions[user_id]['exercises'][current_exercise]['description'] = description
        current_exercise += 1
        if current_exercise < len(self.sessions[user_id]['exercises']):
            self.sessions[user_id]['current_exercise'] = current_exercise
            await update.message.reply_text(
                f"{self.sessions[user_id]['exercises'][current_exercise]['type']} exercise - talk to me")
        else:
            await update.message.reply_text("🤸 All exercises collected🤸 \nType "
                                            "'end' to move to "
                                            "additional questions and save to Notion \nor 'add' - to add a custom exercise")

    async def stop(self, update: Update, context: CallbackContext) -> int:
        user_id = update.message.from_user.id
        if user_id in self.sessions:
            del self.sessions[user_id]
        await update.message.reply_text('Stopped the logging of the lesson.')
        return ConversationHandler.END

    async def set_webhook(self):
        webhook_url = self.webhook_url
        set_webhook_url = f"https://api.telegram.org/bot{self.telegram_token}/setWebhook?url={webhook_url}&secret_token={SECRET_TOKEN}"
        response = requests.post(set_webhook_url)
        if response.status_code == 200:
            print("Webhook set successfully")

    async def run(self):
        await self.application.run_webhook(
            webhook_url=f"https://api.telegram.org/bot{self.telegram_token}/setWebhook?url=https://iu209iyrva.execute-api.us-east-1.amazonaws.com/default/telegram&secret_token=OeIeoDV8o82dNwMlUrOm11vxHb2YyYDs1PA8B5QS",
            secret_token="OeIeoDV8o82dNwMlUrOm11vxHb2YyYDs1PA8B5QS")
        # NO - we want webhook instead of polling
        # self.application.run_polling()

# if __name__ == '__main__':
#     from dotenv import load_dotenv
#     import os

#     load_dotenv()

#     TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
#     NOTION_TOKEN = os.getenv('NOTION_TOKEN')
#     NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
#     GOOGLE_SHEETS_CREDENTIALS_FILE = 'credentials.json'
#     GOOGLE_SHEETS_ID = os.getenv('GOOGLE_SHEETS_ID')

#     bot = TelegramBot(
#         TELEGRAM_TOKEN,
#         NOTION_TOKEN,
#         NOTION_DATABASE_ID,
#         GOOGLE_SHEETS_CREDENTIALS_FILE,
#         GOOGLE_SHEETS_ID
#     )
#     bot.run()
