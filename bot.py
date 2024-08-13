import logging
import re
from typing import Optional

import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler

from utilities.constants import EXPLANATIONS_TEXT
from utilities.google_sheets_client import GoogleSheetsClient
from models.session import UserSession
from models.workout_log import ExerciseUnitLog
from utilities.collections import neutralize_str
from utilities.time import time_for_exer_log


class TelegramBot:
    WORKOUT_TYPE, COLLECT_EXERCISE_RECORDS, _COLLECT_EXERCISE_RECORD, USE_PREVIOUS_EXERCISE_RECORD, SET_EXERCISE_VARIATION, SET_EXERCISE_LEVEL, SET_REP_SEC= range(7)

    def __init__(self, telegram_token,
                 google_sheets_credentials_file, google_main_sheet_doc_id, google_user_template_doc_id, google_user_log_folder_id,
                 webhook_url, secret_token, telegram_user_id, logger=None):
        self.telegram_token = telegram_token
        self.google_sheets_client = GoogleSheetsClient(
            google_sheets_credentials_file,
            google_main_sheet_doc_id,
            google_user_template_doc_id,
            google_user_log_folder_id
        )
        self.sessions = {}
        self.secret_token = secret_token
        self.webhook_url = webhook_url
        self.telegram_user_id = int(telegram_user_id)
        self.logger = logger  # !!TODO: remove pre deploy

        # Configure logging
        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

        self.application = Application.builder().read_timeout(
            10).write_timeout(10).token(
            self.telegram_token).build()

        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', self.new_session)],
            states={
                # self.WORKOUT_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.workout_type)],
                self.COLLECT_EXERCISE_RECORDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_exercise_records)],
                self._COLLECT_EXERCISE_RECORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_exercise_record)],
                self.USE_PREVIOUS_EXERCISE_RECORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.use_previous_exercise_record)],
                self.SET_EXERCISE_VARIATION: [MessageHandler(None, self.set_exercise_variation)],
                self.SET_EXERCISE_LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_exercise_level)],
                self.SET_REP_SEC: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_exercise_rep_sec)],
            },
            fallbacks=[CommandHandler('stop', self.stop)],
            # allow_reentry=True
        )

        self.application.add_handler(conv_handler)
        self.application.add_handler(CommandHandler("start", self.start))
        self.application.add_handler(CommandHandler("stop", self.stop))
        self.application.add_handler(CommandHandler("cancel", self.cancel))
        # self.application.add_handler(CommandHandler("status", self.view_status))

    async def start(self, update: Update, context: CallbackContext) -> Optional[int]:
        user_id = update.message.from_user.id
        print(f" user_id: {user_id}; self.telegram_user_id: {self.telegram_user_id}")
        if user_id != self.telegram_user_id:
            print(f"user id is {user_id} instead of {self.telegram_user_id}")
            await update.message.reply_text("Access denied. You are not authorized to use this bot.")
            return
        await update.message.reply_text('Welcome! Use /start to start '
                                        'logging a new lesson. 💪')

    async def cancel(self, update: Update, context: CallbackContext) -> int:
        user_id = update.message.from_user.id
        if user_id in self.sessions:
            self.sessions.pop(user_id)
        await update.message.reply_text('Cancelled workout log.')
        return ConversationHandler.END

    def create_new_session(self, user_id) -> None:
        self.logger.log("create_new_session()")
        self.sessions[user_id] = UserSession(user_id=user_id)

    async def collect_exercise_records(self, update, context) -> int:  # we'll see if this is a handler or a [[reg method]]
        self.logger.log("collect_exercise_records()")
        user_id = update.message.from_user.id
        workout_type = update.message.text
        self.sessions[user_id].workout_log.type = workout_type
        exercise_list = self.google_sheets_client.get_exercise_list_by_type(self.sessions[user_id].workout_log.type)
        self.sessions[user_id].workout_log.populate_exercises(exercise_list)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Let's start logging!")
        await context.update_queue.put(update)
        return self._COLLECT_EXERCISE_RECORD

    async def collect_exercise_record(self, update, context):
        self.logger.log("collect_exercise_record()")

        user_id = update.message.from_user.id
        curr_ex_id = context.chat_data.get('ex_id')
        if curr_ex_id == self.sessions[user_id].workout_log.exercise_count():
            return await self.end_session(update, context)
        self.sessions[user_id].current_exercise = self.sessions[user_id].workout_log.get_exercise_by_id(curr_ex_id)  # no need to keep track of current if I loop through them
        # check if any previous record
        latest_record = self.sessions[user_id].workout_log.last_exercise_of_same_type(self.sessions[user_id].current_exercise)
        if latest_record is None:
            latest_record = self.google_sheets_client.get_exercise_last_log(user_id, self.sessions[user_id].current_exercise)
        if latest_record is not None:
            context.chat_data['latest_record'] = latest_record
            # Last time you did exercise_last_log.variation in exercise_last_log.level. Do you want to do the same or different?
            await update.message.reply_text(
                f'Use same definition as last time?\n  {latest_record.variation} | {latest_record.level} | {latest_record.rep_sec}',
                reply_markup=ReplyKeyboardMarkup(
                    ['same', 'different'],
                    one_time_keyboard=True))
            return self.USE_PREVIOUS_EXERCISE_RECORD
        else:
            try:
                await update.message.reply_text(
                    f'This is your first time logging {self.sessions[user_id].current_exercise.type}!\nChoose a variation:',
                    reply_markup=ReplyKeyboardMarkup(
                        [self.google_sheets_client.get_exercise_variation_list(self.sessions[user_id].current_exercise.type)],
                        one_time_keyboard=True))
                return self.SET_EXERCISE_VARIATION
            except Exception as e:
                self.logger.log("oops!")
                self.logger.log(str(e))

    async def use_previous_exercise_record(self, update: Update, context: CallbackContext):
        self.logger.log("use_previous_exercise_record()")
        user_id = update.message.from_user.id
        user_choice = update.message.text
        if user_choice == 'same':
            latest_record = context.chat_data.get('latest_record')
            self.sessions[user_id].current_exercise.variation=latest_record.variation
            self.sessions[user_id].current_exercise.level=latest_record.level
            self.sessions[user_id].current_exercise.rep_sec=latest_record.rep_sec
            context.chat_data['ex_id'] += 1
            return self.collect_exercise_record(update, context)
        else:
            await update.message.reply_text(
                f"rep/sec: (. to use {context.chat_data.get('latest_record').rep_sec}")
            return self.SET_REP_SEC

    async def set_exercise_rep_sec(self, update: Update, context: CallbackContext):
        self.logger.log("set_exercise_rep_sec()")
        user_id = update.message.from_user.id
        # possible choices: '.' / <rep_sec>
        user_choice = update.message.text
        if user_choice.strip() == '.':
            rep_sec = context.chat_data.get('latest_record').rep_sec
        else:
            rep_sec = user_choice.strip()
        self.sessions[user_id].current_exercise.rep_sec = rep_sec
        if self.sessions[user_id].current_exercise.level is None:
            await update.message.reply_text('Choose level',
                                            reply_markup=ReplyKeyboardMarkup(
                                                [self.google_sheets_client.get_exercise_variation_level_list(
                                                    self.sessions[user_id].current_exercise.type,
                                                    self.sessions[user_id].current_exercise.variation)],
                                                one_time_keyboard=True))
        return await self.collect_exercise_record(update, context)

    async def set_exercise_level(self, update: Update, context: CallbackContext):
        self.logger.log("set_exercise_level()")
        user_id = update.message.from_user.id
        # possible choices: '.' / <l>
        user_choice = update.message.text
        if user_choice.strip() == '.':
            level = context.chat_data.get('latest_record').level
        else:
            level = user_choice.strip()
        self.sessions[user_id].current_exercise.level = level
        if self.sessions[user_id].current_exercise.variation is None:
            await update.message.reply_text('Choose variation',
                                            reply_markup=ReplyKeyboardMarkup(
                                                [self.google_sheets_client.get_exercise_variation_list(self.sessions[user_id].current_exercise.type)],
                                                one_time_keyboard=True))
            return self.SET_EXERCISE_VARIATION
        await update.message.reply_text(
            f"rep/sec: (. to use {context.chat_data.get('latest_record').rep_sec}")
        return self.SET_REP_SEC

    async def set_exercise_variation(self, update: Update, context: CallbackContext):
        self.logger.log("set_exercise_variation()")
        user_id = update.message.from_user.id
        user_choice = update.message.text
        if user_choice.strip() == '.':
            variation = context.chat_data.get('latest_record').variation
        else:
            variation = user_choice.strip()
        self.sessions[user_id].current_exercise.variation = variation
        if self.sessions[user_id].current_exercise.level is None:
            await update.message.reply_text('Choose level',
                                            reply_markup=ReplyKeyboardMarkup(
                                                [self.google_sheets_client.get_exercise_variation_level_list(self.sessions[user_id].current_exercise, variation)],
                                                one_time_keyboard=True))

            return self.SET_EXERCISE_LEVEL
        context.chat_data['ex_id'] += 1
        return self.collect_exercise_record

    async def end_session(self, update, context: CallbackContext):
        self.logger.log("end_session()")
        # store the session in the user's db
        user_id = update.message.from_user.id
        self.sessions[user_id].spreadsheet_id = self.google_sheets_client.get_user_sheet_doc_id_by_user_id(user_id)
        self.google_sheets_client.log_workout(self.sessions[user_id])
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"Workout Session logged successfully!")
        self.sessions.pop(user_id)
        return ConversationHandler.END

    async def view_status(self, update: Update, context: CallbackContext) -> None:
        user_id = update.message.from_user.id
        if user_id not in self.sessions:
            await update.message.reply_text("No active session found. Use /start to begin logging a new lesson.")
            return

        log_data = self._sessions[user_id]
        status_message = f"Current log data:\n\nType: {log_data.type.capitalize()}\nCoach: {log_data['coach']}\nExercises:\n"

        for idx, exercise in enumerate(log_data.exercises):
            status_message += f"{idx + 1}. {exercise.type} - {exercise.variation}\n"

        if 'custom_exercises' in log_data:
            status_message += "\nCustom Exercises:\n"
            for idx, exercise in enumerate(log_data['custom_exercises']):
                status_message += f"{idx + 1}. {exercise['type']} - {exercise['description']}\n"

        await update.message.reply_text(status_message)

    async def new_session(self, update: Update, context: CallbackContext) -> int:
        self.logger.log("new_session()")
        user_id = update.message.from_user.id
        print(f"User ID: {user_id}")
        self.create_new_session(user_id)
        await update.message.reply_text('Is it a "Strength" or "Skill" session?',
                                        reply_markup=ReplyKeyboardMarkup([self.google_sheets_client.get_workout_type_list()],
                                                                         one_time_keyboard=True))
        context.chat_data['ex_id'] = 0
        return self.COLLECT_EXERCISE_RECORDS

    async def choose_type(self, update: Update, context: CallbackContext) -> int:
        user_id = update.message.from_user.id
        lesson_type = update.message.text.lower()
        self.sessions[user_id]['type'] = lesson_type
        self._sessions[user_id].workout_log.type = lesson_type
        await update.message.reply_text('Who is the coach?',
                                        reply_markup=ReplyKeyboardMarkup([self.google_sheets_client.get_trainer_list()],
                                                                         one_time_keyboard=True))
        return self.EXERCISE_TYPE

    async def exercise_type(self, update: Update, context: CallbackContext) -> int:
        user_id = update.message.from_user.id
        lesson_type = update.message.text.lower()
        self.sessions[user_id]['type'] = lesson_type
        self._sessions[user_id].workout_log.type = lesson_type
        await update.message.reply_text('Who is the coach?',
                                        reply_markup=ReplyKeyboardMarkup([self.google_sheets_client.get_trainer_list()],
                                                                         one_time_keyboard=True))
        return self.EXERCISE_TYPE

    async def choose_coach(self, update: Update, context: CallbackContext) -> int:
        user_id = update.message.from_user.id
        coach = update.message.text
        self.sessions[user_id]['coach'] = coach
        exercise_list = self.google_sheets_client.get_exercise_list_by_type(self._sessions[user_id].workout_log.type)
        self.sessions[user_id]['exercises'] = [{'type': ex, 'description': ''} for ex in exercise_list]
        self._sessions[user_id].workout_log.exercises = [ExerciseUnitLog(type=ex_name) for ex_name in exercise_list for _ in range(3)]
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"Starting {self.sessions[user_id]['type']} lesson with {coach}. Let's start with the exercises.")
        # await context.bot.send_message(chat_id=update.effective_chat.id,
        #                                text=f"{self._sessions[user_id].workout_log.exercises[0].type} - talk to me.")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=EXPLANATIONS_TEXT)
        return self.COLLECTING_DESCRIPTIONS

    async def add_custom_exercise(self, update: Update, context: CallbackContext) -> int:
        user_id = update.message.from_user.id
        custom_exercise_title = update.message.text
        self.sessions[user_id]['custom_exercise_title'] = custom_exercise_title
        self._sessions[user_id].workout_log.custom_exercises.append(ExerciseUnitLog(type=custom_exercise_title))
        await context.bot.send_message(chat_id=update.effective_chat.id, text='Enter the custom exercise description:')
        return self.ADDING_CUSTOM_DESCRIPTION

    async def add_custom_description(self, update: Update, context: CallbackContext) -> int:
        user_id = update.message.from_user.id
        custom_exercise_variation = update.message.text
        custom_exercise = self._sessions[user_id].custom_exercises[-1]
        custom_exercise.variation = custom_exercise_variation
        if 'custom_exercises' not in self.sessions[user_id]:
            self.sessions[user_id]['custom_exercises'] = []
        self.sessions[user_id]['custom_exercises'].append(custom_exercise)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text='Custom exercise was added '
                                            'successfully.')
        if 'current_exercise' not in self.sessions[user_id]:
            self.sessions[user_id]['current_exercise'] = 0
        current_exercise = self._sessions[user_id].current_exercise
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"{self.sessions[user_id]['exercises'][current_exercise]['type']} exercise - talk to me")
        await context.bot.send_message(chat_id=update.effective_chat.id, text=EXPLANATIONS_TEXT)
        return self.COLLECTING_DESCRIPTIONS

    async def collect_description(self, update: Update, context: CallbackContext) -> int:
        user_id = update.message.from_user.id
        user_response = update.message.text
        if neutralize_str(user_response) == "end":
            await update.message.reply_text("All exercises were collected. "
                                            "Now, "
                                            "let's answer a few additional "
                                            "questions.")
            return await self.ask_additional_questions(update, context)

        elif user_response.lower() == "skip":
            await self.skip_exercise(update, user_id)
            return self.COLLECTING_DESCRIPTIONS

        elif user_response.lower() == "add":
            await context.bot.send_message(chat_id=update.effective_chat.id, text='Enter the custom exercise title:')
            return self.ADDING_CUSTOM_EXERCISE

        else:
            context.chat_data.set('exer_rep_time', user_response)
            await self.add_exer_log(update, context)
            return self.COLLECTING_DESCRIPTIONS

    async def prev_exercise(self, update: Update, context: CallbackContext) -> int:
        # TODO: Refactor
        user_id = update.message.from_user.id
        if 'current_exercise' not in self.sessions[user_id]:
            self.sessions[user_id]['current_exercise'] = 0
        current_exercise = self.sessions[user_id]['current_exercise']
        if current_exercise > 0:
            current_exercise -= 1
            self.sessions[user_id]['current_exercise'] = current_exercise
            await update.message.reply_text(
                f"Going back to the previous exercise: {self.sessions[user_id]['exercises'][current_exercise]['type']} - talk to me.\nCurrent description: {self.sessions[user_id]['exercises'][current_exercise]['description']}")
        else:
            await update.message.reply_text("You are at the first exercise.")
        return self.COLLECTING_DESCRIPTIONS

    async def next_exercise(self, update: Update, context: CallbackContext) -> int:
        # TODO: Refactor
        user_id = update.message.from_user.id
        if 'current_exercise' not in self.sessions[user_id]:
            self.sessions[user_id]['current_exercise'] = 0
        current_exercise = self.sessions[user_id]['current_exercise']
        if current_exercise < len(self.sessions[user_id]['exercises']) - 1:
            current_exercise += 1
            self.sessions[user_id]['current_exercise'] = current_exercise
            await update.message.reply_text(
                f"Going to the next exercise: {self.sessions[user_id]['exercises'][current_exercise]['type']} - talk to me.\nCurrent description: {self.sessions[user_id]['exercises'][current_exercise]['description']}")
        else:
            await update.message.reply_text("You are at the last exercise.")
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
            await update.message.reply_text('exercise was skipped.')
            await update.message.reply_text('🤸 All exercises collected🤸 \nType '
                                            '"end" to move to additional '
                                            'questions and save to Notion\nOr "add" - to add a custom exercise')
        else:
            self.sessions[user_id]['current_exercise'] = current_exercise
            await update.message.reply_text(EXPLANATIONS_TEXT)
            await update.message.reply_text(
                f"{self.sessions[user_id]['exercises'][current_exercise]['type']} - talk to me.")

    def escape_markdown_v2(self, text):
        escape_chars = r'_*\[\]()~`>#+-=|{}.!\\'

        # Regular expression to find characters that need to be escaped but aren't
        pattern = re.compile(r'(?<!\\)([' + re.escape(escape_chars) + '])')

        # Replace the characters with escaped versions
        return pattern.sub(r'\\\1', text)

    async def choose_exercise_variation(self, update, context: CallbackContext):
        exercise_type = update.message.text
        context.chat_data.set('exercise_type', exercise_type)
        exercise_variations = self.google_sheets_client.get_exercise_variation_list(exercise_type)

        await update.message.reply_text('Choose variation',
                                        reply_markup=ReplyKeyboardMarkup(
                                            [exercise_variations],
                                            one_time_keyboard=True))

    async def choose_exercise_level(self, update, context: CallbackContext):
        exercise_variation = update.message.text
        exercise_type = context.chat_data.get("exercise_type")
        exercise_variation_levels = self.google_sheets_client.get_exercise_variation_level_list(exercise_type, exercise_variation)

        await update.message.reply_text('Choose level',
                                        reply_markup=ReplyKeyboardMarkup(
                                            [exercise_variation_levels],
                                            one_time_keyboard=True))

    async def choose_same_or_diff_exercise_definition(self, update, context: CallbackContext):
        same_or_diff = update.message.text
        # exercise_variation_levels = self.google_sheets_client.get_exercise_variation_level_list(exercise)
        if neutralize_str(same_or_diff) == 'same':
            return self.HANDLE_SAME_EXERCISE_DEFINITION
        else:
            return self.HANDLE_DIFF_EXERCISE_DEFINITION

    async def handle_same_exercise_definition(self, update, context: CallbackContext):
        user_id = update.effective_user.id
        exercise_variation = context.chat_data.get('latest_record').variation
        exercise_level = context.chat_data.get('latest_record').level
        self._sessions[user_id].current_exercise.variation = exercise_variation
        self._sessions[user_id].current_exercise.level = exercise_level

    async def change_exercise_definition_menu(self, update, context: CallbackContext):
        user_id = update.effective_user.id
        await update.message.reply_text(
            f'What changed?',
            reply_markup=ReplyKeyboardMarkup(
                ['Number of Reps/Secs', 'Level', 'Variation'],
                one_time_keyboard=True))
        # TODO: Add handler

    async def add_exer_log(self, update: Update, context: CallbackContext):
        # TODO [not MVP]: ask user if they have notes
        user_id = update.effective_user.id
        exer_rep_time = context.chat_data.get('exer_rep_time')

        if self._sessions[user_id].current_exercise is None:
            self._sessions[user_id].current_exercise = self._sessions[user_id].workout_log.exercises[0]
        current_exercise = self._sessions[user_id].current_exercise
        # If user has already done this exercise, ask if they wanna do the same var/lev as last time
        # 1. in this session
        exercise_last_log = self._sessions[user_id].workout_log.last_exercise_of_same_type(current_exercise)
        if exercise_last_log is None:
            # 2. in last session
            exercise_last_log = self.google_sheets_client.get_exercise_last_log(user_id, current_exercise)
        if exercise_last_log is not None:
            context.chat_data['latest_record'] = exercise_last_log
            # Last time you did exercise_last_log.variation in exercise_last_log.level. Do you want to do the same or different?
            await update.message.reply_text(f'Use same variation/level as last time?\n  {exercise_last_log.variation} | {exercise_last_log.level}',
                                            reply_markup=ReplyKeyboardMarkup(
                                                ['same', 'different'],
                                                one_time_keyboard=True))
            return self.CHOOSING_SAME_DIFF_EXERCISE_DEFINITION
        else:
            await update.message.reply_text('This is your first time logging this exercise!\nPlease choose a variation:')
            return self.CHOOSING_EXERCISE_VARIATION
            pass
            # exercise_variations = self.google_sheets_client.get_exercise_variation_list(exercise)
            await update.message.reply_text('Choose variation',
                                            reply_markup=ReplyKeyboardMarkup(
                                                [exercise_variations],
                                                one_time_keyboard=True))

        current_exercise.time = time_for_exer_log()
        current_exercise.rep_sec = exer_rep_time
        if current_exercise < len(self._sessions[user_id].workout_log.exercises):
            self.sessions[user_id]['current_exercise'] = current_exercise
            self._sessions[user_id].current_exercise = current_exercise
            await update.message.reply_text(
                f"{self.sessions[user_id]['exercises'][current_exercise]['type']} exercise - talk to me")
        else:
            await update.message.reply_text("🤸 All exercises collected🤸 \nType "
                                            "'end' to move to "
                                            "additional questions and save to Notion \nor 'add' - to add a custom exercise")

    async def stop(self, update: Update, context: CallbackContext) -> int:
        # TODO: Why stop AND end?
        user_id = update.message.from_user.id
        if user_id in self.sessions:
            del self.sessions[user_id]
            self._sessions.pop(user_id)
        await update.message.reply_text('Stopped the logging of the lesson.')
        return ConversationHandler.END

    def set_webhook(self):
        webhook_url = self.webhook_url
        set_webhook_url = f"https://api.telegram.org/bot{self.telegram_token}/setWebhook?url={webhook_url}&secret_token={self.secret_token}"
        response = requests.post(set_webhook_url)
        print("RESP: {response}")
        if response.status_code == 200:
            print("Webhook set successfully")

