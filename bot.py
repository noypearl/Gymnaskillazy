import logging
from typing import Optional

import requests
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler

from models.session import UserSession
from utilities.collections import neutralize_str
from utilities.constants import EXPLANATIONS_TEXT, SAME_OR_DIFFERENT
from utilities.google_sheets_client import GoogleSheetsClient
from utilities.telegram import InputValidation
from utilities.time import time_for_exer_log


class TelegramBot:
    START, _CONFIG, EDIT_SETTINGS, SUBMIT_SETTINGS, COLLECT_EXERCISE_RECORDS, _COLLECT_EXERCISE_RECORD, USE_PREVIOUS_EXERCISE_RECORD, SET_EXERCISE_VARIATION, SET_EXERCISE_LEVEL, SET_REP_SEC= range(10)

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

        self.application = (Application.builder()
                            .get_updates_read_timeout(3600)
                            .get_updates_write_timeout(3600).token(
            self.telegram_token).build())

        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', self.start),
                CommandHandler('config', self.config),
                CommandHandler('unauthorized', self.unauthorized),
                CommandHandler('cancel', self.cancel)
            ],
            states={
                self.START: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.start)],
                self._CONFIG: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.config)],
                self.EDIT_SETTINGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.edit_settings)],
                self.SUBMIT_SETTINGS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.submit_settings)],
                self.COLLECT_EXERCISE_RECORDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_exercise_records)],
                self._COLLECT_EXERCISE_RECORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.collect_exercise_record)],
                self.USE_PREVIOUS_EXERCISE_RECORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.use_previous_exercise_record)],
                self.SET_EXERCISE_VARIATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_exercise_variation)],
                self.SET_EXERCISE_LEVEL: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_exercise_level)],
                self.SET_REP_SEC: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.set_exercise_rep_sec)],
            },
            fallbacks=[CommandHandler('error', self.error)],
        )

        self.application.add_handler(conv_handler)
        self.application.add_handler(CommandHandler("config", self.config))
        self.application.add_handler(CommandHandler('log', self.unauthorized))
        self.application.add_handler(CommandHandler('help', self.unauthorized))
        self.application.add_handler(CommandHandler('cancel', self.unauthorized))

    async def unauthorized(self, update: Update, context: CallbackContext) -> int:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="You're not authorized to use this command")
        return ConversationHandler.END

    async def start(self, update: Update, context: CallbackContext) -> Optional[int]:
        self.logger.log("start()")
        user_id = update.message.from_user.id
        print(f" user_id: {user_id}; self.telegram_user_id: {self.telegram_user_id}")
        user_config = self.google_sheets_client.get_user_config(user_id)
        self.sessions[user_id].user_config = user_config
        user_email = user_config.get('email')
        print(user_email)
        permitted_emails = self.google_sheets_client.get_permitted_user_emails()
        print(permitted_emails)
        if user_email is None:
            msg = "Set your email address in /config to get access to the bot"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
            return ConversationHandler.END
        elif user_email not in permitted_emails:
            msg = "You're not on the guest list!\n" + \
                  "If you're part of the Gymnaskillz family, contact Shahar for an invite."
            await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)
            return ConversationHandler.END
        else:
            self.application.add_handler(CommandHandler('log', self.new_session))
            self.application.add_handler(CommandHandler('help', self.help))
            self.application.add_handler(CommandHandler('cancel', self.cancel))
            msg = "Welcome to the Gymnaskillz logbook bot!\n" + \
                "Hit /log to log a workout! 💪\n" + \
                "Use /help to learn more"
            await context.bot.send_message(chat_id=update.effective_chat.id, text=msg)

    async def cancel(self, update: Update, context: CallbackContext) -> Optional[int]:
        self.logger.log("cancel()")
        user_id = update.message.from_user.id
        if user_id in self.sessions:
            self.cleanup(update, context)
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Cancelled workout log.\nStart a new one? /log")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="No workout session in progress.\nStart a new one? /log")
        return ConversationHandler.END

    async def help(self, update: Update, context: CallbackContext) -> None:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Under construction")

    def prep_session(self, user_id: int) -> None:
        if self.sessions.get(user_id) is None:
            self.sessions[user_id] = UserSession(user_id)
        if self.sessions[user_id].spreadsheet_doc is None:
            self.sessions[user_id].set_spreadsheet_doc(self.google_sheets_client.get_user_doc_by_user_id(user_id))

    async def config(self, update: Update, context: CallbackContext) -> int:
        self.logger.log("config()")
        user_id = update.message.from_user.id
        self.prep_session(user_id)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Loading your settings...")
        user_config = self.sessions[user_id].user_config
        msg = "Your settings:"
        for setting, value in user_config.items():
            msg += f"\n{setting}: {value}"
        msg += f"\nWhat would you like to edit?"
        keyboard_options = list(user_config.keys()) + ["all good"]
        context.chat_data['prev_step_options'] = keyboard_options
        await update.message.reply_text(msg,
                                        reply_markup=ReplyKeyboardMarkup(
                                            [keyboard_options],
                                            one_time_keyboard=True))
        return self.EDIT_SETTINGS

    async def edit_settings(self, update: Update, context: CallbackContext) -> int:
        self.logger.log("edit_settings()")
        user_id = update.message.from_user.id
        user_choice = update.message.text
        user_config = self.sessions[user_id].user_config
        expected_values = context.chat_data['prev_step_options']
        if not InputValidation.accepted_value(user_choice, expected_values):
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid choice.")
            await context.update_queue.put(update)
            return self._CONFIG
        if neutralize_str(user_choice) == "all good":
            await context.update_queue.put(update)
            return self.START
        context.chat_data['user_config_pointer'] = user_choice
        msg = "What should the new value be?"
        if user_config.get(user_choice) is not None:
            msg += f" (press '.' for {user_config.get(user_choice)})"
        await update.message.reply_text(msg)
        return self.SUBMIT_SETTINGS

    async def submit_settings(self, update: Update, context: CallbackContext) -> int:
        self.logger.log("submit_settings()")
        user_id = update.message.from_user.id
        user_choice = neutralize_str(update.message.text)
        if neutralize_str(user_choice) == ".":
            await context.update_queue.put(update)
            return self._CONFIG
        user_config = self.sessions[user_id].user_config
        setting_name = context.chat_data.get('user_config_pointer')
        if user_choice != user_config.get(setting_name):
            self.google_sheets_client.update_settings(self.sessions[user_id].spreadsheet_doc, setting_name, user_choice)
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Up to date!")
        await context.update_queue.put(update)
        return self._CONFIG

    async def new_session(self, update: Update, context: CallbackContext) -> int:
        self.logger.log("new_session()")
        user_id = update.message.from_user.id
        print(f"User ID: {user_id}")
        self.prep_session(user_id)
        await update.message.reply_text('What type of workout today, champ?',
                                        reply_markup=ReplyKeyboardMarkup([self.google_sheets_client.get_workout_type_list()],
                                                                         one_time_keyboard=True))
        return self.COLLECT_EXERCISE_RECORDS

    async def collect_exercise_records(self, update, context) -> int:
        self.logger.log("collect_exercise_records()")
        user_id = update.message.from_user.id
        workout_type = update.message.text
        self.sessions[user_id].workout_log.type = workout_type
        exercise_list = self.google_sheets_client.get_exercise_list_by_type(self.sessions[user_id].workout_log.type)
        self.sessions[user_id].workout_log.populate_exercises(exercise_list)
        context.chat_data['ex_id'] = self.sessions[user_id].workout_log.min_exercise_id()
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Loading your data...")
        await context.update_queue.put(update)
        return self._COLLECT_EXERCISE_RECORD

    async def collect_exercise_record(self, update, context):
        self.logger.log("collect_exercise_record()")
        user_id = update.message.from_user.id
        curr_ex_id = context.chat_data.get('ex_id')
        if curr_ex_id > self.sessions[user_id].workout_log.max_exercise_id():
            return await self.end_session(update, context)
        self.sessions[user_id].current_exercise = self.sessions[user_id].workout_log.get_exercise_by_id(curr_ex_id)
        # check if any previous record
        latest_record = self.sessions[user_id].workout_log.last_exercise_of_same_type(self.sessions[user_id].current_exercise)
        if latest_record is None:
            latest_record = self.google_sheets_client.get_exercise_last_log(user_id, self.sessions[user_id].current_exercise)
        context.chat_data['latest_record'] = latest_record
        if latest_record is not None:
            await update.message.reply_text(
                f'{latest_record.type}\nUse same definition as last time?\n\t\t{latest_record.variation} | {latest_record.level} | {latest_record.rep_sec}',
                reply_markup=ReplyKeyboardMarkup(
                    [SAME_OR_DIFFERENT],
                    one_time_keyboard=True))
            return self.USE_PREVIOUS_EXERCISE_RECORD
        else:
            keyboard_options = self.google_sheets_client.get_exercise_variation_list(self.sessions[user_id].current_exercise.type)
            context.chat_data['prev_step_options'] = keyboard_options
            await update.message.reply_text(
                f'This is your first time logging {self.sessions[user_id].current_exercise.type}!\nChoose a variation:',
                reply_markup=ReplyKeyboardMarkup(
                    [keyboard_options],
                    one_time_keyboard=True))
            return self.SET_EXERCISE_VARIATION

    async def use_previous_exercise_record(self, update: Update, context: CallbackContext):
        self.logger.log("use_previous_exercise_record()")
        user_id = update.message.from_user.id
        user_choice = update.message.text
        if not InputValidation.accepted_value(user_choice, SAME_OR_DIFFERENT):
            await update.message.reply_text(f'Invalid choice.')
            return self.USE_PREVIOUS_EXERCISE_RECORD
        latest_record = context.chat_data.get('latest_record')
        if user_choice == 'same':
            self.sessions[user_id].current_exercise.variation=latest_record.variation
            self.sessions[user_id].current_exercise.level=latest_record.level
            self.sessions[user_id].current_exercise.rep_sec=latest_record.rep_sec
            self.complete_exercise_log(update, context)
            await context.update_queue.put(update)
            return self._COLLECT_EXERCISE_RECORD
        else:
            msg = "rep/sec:"
            if latest_record is not None:
                msg += f" (press '.' to use {latest_record.rep_sec})"
            await update.message.reply_text(msg)
            return self.SET_REP_SEC

    async def set_exercise_rep_sec(self, update: Update, context: CallbackContext):
        self.logger.log("set_exercise_rep_sec()")
        user_id = update.message.from_user.id
        # possible choices: '.' / <rep_sec>
        user_choice = update.message.text
        if not InputValidation.digit_or_dot(user_choice):
            await update.message.reply_text("Please enter either a numerical value or a dot")
            return self.SET_REP_SEC
        latest_record = context.chat_data.get('latest_record')
        if latest_record is None and neutralize_str(user_choice) == '.':
            # TODO: if no latest_record, take user input until it's not '.'
            await update.message.reply_text("No prior data for that. Input the value manually")
            return self.SET_REP_SEC
        if neutralize_str(user_choice) == '.':
            rep_sec = latest_record.rep_sec
        else:
            rep_sec = user_choice.strip()
        self.sessions[user_id].current_exercise.rep_sec = int(rep_sec)
        if self.sessions[user_id].current_exercise.variation is None:
            keyboard_options = self.google_sheets_client.get_exercise_variation_list(self.sessions[user_id].current_exercise.type)
            if latest_record is not None:
                keyboard_options += ["same"]
            context.chat_data['prev_step_options'] = keyboard_options
            await update.message.reply_text('Choose variation',
                                            reply_markup=ReplyKeyboardMarkup(
                                                [keyboard_options],
                                                one_time_keyboard=True))
            return self.SET_EXERCISE_VARIATION
        self.complete_exercise_log(update, context)
        await context.update_queue.put(update)
        return self._COLLECT_EXERCISE_RECORD

    async def set_exercise_level(self, update: Update, context: CallbackContext):
        self.logger.log("set_exercise_level()")
        user_id = update.message.from_user.id
        user_choice = update.message.text
        if not InputValidation.accepted_value(user_choice, context.chat_data['prev_step_options']):
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid choice.")
            await update.message.reply_text('Choose level',
                                            reply_markup=ReplyKeyboardMarkup(
                                                [context.chat_data['prev_step_options']],
                                                one_time_keyboard=True))

            return self.SET_EXERCISE_LEVEL
        if neutralize_str(user_choice) == 'same':
            level = context.chat_data.get('latest_record').level
        else:
            level = user_choice.strip()
        self.sessions[user_id].current_exercise.level = level
        if self.sessions[user_id].current_exercise.rep_sec is None:
            msg = "rep/sec:"
            if context.chat_data.get('latest_record') is not None:
                msg += f" (press '.' to use {context.chat_data.get('latest_record').rep_sec})"
            await update.message.reply_text(msg)
            return self.SET_REP_SEC
        self.complete_exercise_log(update, context)
        await context.update_queue.put(update)
        return self._COLLECT_EXERCISE_RECORD

    async def set_exercise_variation(self, update: Update, context: CallbackContext):
        self.logger.log("set_exercise_variation()")
        user_id = update.message.from_user.id
        user_choice = update.message.text
        if not InputValidation.accepted_value(user_choice, context.chat_data['prev_step_options']):
            await context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid choice.")
            await update.message.reply_text('Choose variation',
                                            reply_markup=ReplyKeyboardMarkup(
                                                [context.chat_data['prev_step_options']],
                                                one_time_keyboard=True))

            return self.SET_EXERCISE_VARIATION
        if neutralize_str(user_choice) == 'same':
            variation = context.chat_data.get('latest_record').variation
            keyboard_options = ["same"]
        else:
            variation = user_choice.strip()
            keyboard_options = []
        keyboard_options = self.google_sheets_client.get_exercise_variation_level_list(self.sessions[user_id].current_exercise.type, variation) + keyboard_options
        context.chat_data['prev_step_options'] = keyboard_options
        self.sessions[user_id].current_exercise.variation = variation
        await update.message.reply_text('Choose level',
                                        reply_markup=ReplyKeyboardMarkup(
                                            [keyboard_options],
                                            one_time_keyboard=True))

        return self.SET_EXERCISE_LEVEL

    def complete_exercise_log(self, update: Update, context: CallbackContext):
        user_id = update.message.from_user.id
        context.chat_data['ex_id'] += 1
        self.sessions[user_id].current_exercise.time = time_for_exer_log()

    async def end_session(self, update, context: CallbackContext):
        self.logger.log("end_session()")
        # TODO: Display log, ask if they want to edit
        # store the session in the user's DB
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"Logging your workout...")
        user_id = update.message.from_user.id
        self.google_sheets_client.log_workout(self.sessions[user_id])
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=f"Workout session logged successfully!")

        self.cleanup(update, context)
        return ConversationHandler.END

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

    async def skip_exercise(self, update: Update, user_id):
        # TODO: Refactor
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

    def set_webhook(self):
        webhook_url = self.webhook_url
        set_webhook_url = f"https://api.telegram.org/bot{self.telegram_token}/setWebhook?url={webhook_url}&secret_token={self.secret_token}"
        response = requests.post(set_webhook_url)
        print("RESP: {response}")
        if response.status_code == 200:
            print("Webhook set successfully")

    def cleanup(self, update, context):
        user_id = update.message.from_user.id
        if user_id in self.sessions:
            self.sessions.pop(user_id)
        if user_id in self.google_sheets_client.user_docs:
            self.google_sheets_client.user_docs.pop(user_id)
        context.chat_data.clear()

    async def error(self, update: Update, context: CallbackContext):
        print("Whoa! Something happened")
