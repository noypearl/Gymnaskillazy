import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
import requests
import os
import json
import gspread
from dotenv import load_dotenv
from datetime import datetime
from constants import EXPLANATIONS_TEXT, MULTI_TAGS, USER_ID
from oauth2client.service_account import ServiceAccountCredentials

load_dotenv()

# Telegram bot token
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
# Notion integration token
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
# Notion database ID
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')
# Google Sheets credentials file
GOOGLE_SHEETS_CREDENTIALS_FILE = 'path/to/credentials.json'
# Google Sheets ID
GOOGLE_SHEETS_ID = os.getenv('GOOGLE_SHEETS_ID')

# Configure logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


# States for conversation handler
CHOOSING_TYPE, CHOOSING_COACH, GETTING_EXERCISES, COLLECTING_DESCRIPTIONS, ADDING_CUSTOM_EXERCISE, ADDING_CUSTOM_DESCRIPTION = range(6)

# Dictionary to store ongoing sessions
sessions = {}

# Initialize Google Sheets client
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
#credentials = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SHEETS_CREDENTIALS_FILE, scope)
#client = gspread.authorize(credentials)

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text('Welcome! Use /start to start logging a new lesson.')

async def view_status(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    if user_id not in sessions:
        await update.message.reply_text("No active session found. Use /start to begin logging a new lesson.")
        return

    log_data = sessions[user_id]
    status_message = f"Current log data:\n\nType: {log_data['type'].capitalize()}\nCoach: {log_data['coach']}\nExercises:\n"

    for idx, exercise in enumerate(log_data['exercises']):
        status_message += f"{idx + 1}. {exercise['type']} - {exercise['description']}\n"

    if 'custom_exercises' in log_data:
        status_message += "\nCustom Exercises:\n"
        for idx, exercise in enumerate(log_data['custom_exercises']):
            status_message += f"{idx + 1}. {exercise['type']} - {exercise['description']}\n"

    await update.message.reply_text(status_message)

async def new_log(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    print(f"User ID: {user_id}")
    sessions[user_id] = {'exercises': []}
    await update.message.reply_text('Is it a "Strength" or "Skill" lesson?',
                                    reply_markup=ReplyKeyboardMarkup([['Strength', 'Skill']], one_time_keyboard=True))
    return CHOOSING_TYPE

async def choose_type(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    lesson_type = update.message.text.lower()
    sessions[user_id]['type'] = lesson_type
    await update.message.reply_text('Who is the coach? Choose from: Shahar, Alon, Sagi, Yair', reply_markup=ReplyKeyboardMarkup([['Shahar', 'Alon', 'Sagi', 'Yair']], one_time_keyboard=True))
    return CHOOSING_COACH

async def choose_coach(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    coach = update.message.text
    sessions[user_id]['coach'] = coach
    # Pull exercises from Google Sheets
    #sheet = client.open_by_key(GOOGLE_SHEETS_ID).sheet1
    if sessions[user_id]['type'] == 'Strength':
          #      exercise_data = sheet.col_values(1)[1:10]  # A2:A10 TODO - change when sheets integration is ready!
        exercise_data = ["notCrow"]
        #exercise_data = ["notCrow", "Handstand", "Push up"]
    else:
        exercise_data = ["Handstand", "Crow"]
      #  exercise_data = sheet.col_values(2)[1:10]  # B2:B10
    sessions[user_id]['exercises'] = [{'type': ex, 'description': ''} for ex in exercise_data]
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Starting {sessions[user_id]['type']} lesson with {coach}. Let's start with the exercises.")
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=f"{sessions[user_id]['exercises'][0]['type']} - talk to me.")
    await context.bot.send_message(chat_id=update.effective_chat.id,text=EXPLANATIONS_TEXT)
    return COLLECTING_DESCRIPTIONS

async def add_custom_exercise(update: Update, context: CallbackContext) -> int:  # New function to handle custom exercise title
    user_id = update.message.from_user.id
    custom_exercise_title = update.message.text
    sessions[user_id]['custom_exercise_title'] = custom_exercise_title
    await context.bot.send_message(chat_id=update.effective_chat.id, text='Enter the custom exercise description:')
    return ADDING_CUSTOM_DESCRIPTION
async def add_custom_description(update: Update, context: CallbackContext) -> int:  # New function to handle custom exercise description
    user_id = update.message.from_user.id
    custom_exercise_description = update.message.text
    custom_exercise = {
        'type': sessions[user_id]['custom_exercise_title'],
        'description': custom_exercise_description
    }
    if 'custom_exercises' not in sessions[user_id]:
        sessions[user_id]['custom_exercises'] = []
    sessions[user_id]['custom_exercises'].append(custom_exercise)
    await context.bot.send_message(chat_id=update.effective_chat.id, text='Custom exercise added successfully.')
    # Continue with the regular exercise flow
    if 'current_exercise' not in sessions[user_id]:
        sessions[user_id]['current_exercise'] = 0
    current_exercise = sessions[user_id]['current_exercise']
    await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{sessions[user_id]['exercises'][current_exercise]['type']} exercise - talk to me")
    await context.bot.send_message(chat_id=update.effective_chat.id,text=EXPLANATIONS_TEXT)
    return COLLECTING_DESCRIPTIONS


async def collect_description(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    description = update.message.text
    if description.lower() == "end":
        await update.message.reply_text('Updating...')
        page_id = await save_to_notion(user_id, context)
        await append_block_to_page(page_id, user_id)  # Updated: Appending blocks to the Notion page

        # Notify the user of what was logged
        log_data = sessions[user_id]
        status_message = (f"Lesson completed! NOICE!! \n"
                          f"Logged lesson data:\n\nType:"
                          f" {log_data['type'].capitalize()}\nCoach: "
                          f"{log_data['coach']}\n\n\nExercises:\n")

        for idx, exercise in enumerate(log_data['exercises']):
            status_message += f"{idx + 1}. {exercise['type']} - {exercise['description']}\n"

        if 'custom_exercises' in log_data:
            status_message += "\nCustom Exercises:\n"
            for idx, exercise in enumerate(log_data['custom_exercises']):
                status_message += f"{idx + 1}. {exercise['type']} - {exercise['description']}\n"
        await update.message.reply_text(status_message)
        await update.message.reply_text('Lesson data added to Notion successfully!')
        return ConversationHandler.END

    elif description.lower() == "skip":
        if 'current_exercise' not in sessions[user_id]:
            sessions[user_id]['current_exercise'] = 0
        current_exercise = sessions[user_id]['current_exercise']
        current_exercise += 1
        if current_exercise == len(sessions[user_id]['exercises']):
            sessions[user_id]['current_exercise'] = current_exercise
            await context.bot.send_message(chat_id=update.effective_chat.id, text='exercise was skipped.')
            await context.bot.send_message(chat_id=update.effective_chat.id, text='All exercises collected. Type "end" to finish and save to Notion.')
        return COLLECTING_DESCRIPTIONS
    elif description.lower() == "add":  # New handling for "add" command
        await context.bot.send_message(chat_id=update.effective_chat.id, text='Enter the custom exercise title:')
        return ADDING_CUSTOM_EXERCISE
    else:
        if 'current_exercise' not in sessions[user_id]:
            sessions[user_id]['current_exercise'] = 0
        current_exercise = sessions[user_id]['current_exercise']
        sessions[user_id]['exercises'][current_exercise]['description'] = description
        current_exercise += 1
        if current_exercise < len(sessions[user_id]['exercises']):
            sessions[user_id]['current_exercise'] = current_exercise
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{sessions[user_id]['exercises'][current_exercise]['type']} exercise - talk to me")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text="All exercises collected. \n"
                                                "Type 'end' to finish and "
                                                "save to Notion \nor 'add' - to add a custom exercise")
        return COLLECTING_DESCRIPTIONS


async def stop(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    if user_id in sessions:
        del sessions[user_id]
    await update.message.reply_text('Stopped the logging of the lesson.')
    return ConversationHandler.END

def testme():
    data = json.loads(open('data', 'r').read())
    coach = MULTI_TAGS["coach"][data["coach"]]
    type = MULTI_TAGS["type"][data["type"]]
    print(f"type: {type}")
    print(f"coach: {coach} {data['coach']} {coach['id']}")
    exercises_text = "\n\n".join([f"**{ex['type']}**\n{ex['description']}" for ex in data['exercises']])
    date_str = datetime.now().isoformat()
    print(f"CURR DATE: {date_str}")
    url = 'https://api.notion.com/v1/pages'
    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Content-Type': 'application/json',
        'Notion-Version': '2021-05-13'
    }
    payload = {
    'parent': {'database_id': NOTION_DATABASE_ID},
    "object": "page",
    "last_edited_time": datetime.now().isoformat(),
    "created_by": {
        "object": "user",
        "id": "33f7619f-8330-4fb9-9889-706bcd9b6a01"
    },
    "last_edited_by": {
        "object": "user",
        "id": "33f7619f-8330-4fb9-9889-706bcd9b6a01"
    },
    "cover": None,
    "icon": None,
    "parent": {
        "type": "database_id",
        "database_id": "0f05bd21-7122-4d20-af9b-b9b6cdaa2654"
    },
    "archived": False,
    "in_trash": False,
    "properties": {
        "Coach": {
            "id": "aYm;",
            "type": "select",
            "select": {
                "id": coach["id"],
                "name":data['coach'],
                "color": coach["color"],
                "description": None
            }
        },
        "Tags": {
            "id": "bqtJ",
            "type": "multi_select",
            "multi_select": [
                {
                    "id": type["id"],
                    "name":type["name"],
                    "color": type["color"]
                }
            ]
        },
        "AI summary": {
            "id": "n<mr",
            "type": "rich_text",
            "rich_text": []
        },
        "Date": {
            "id": "}DM<",
            "type": "date",
            "date": {
                "start": datetime.now().isoformat(),
                "end": None,
                "time_zone": None
            }
        },
        "Name": {
            "id": "title",
            "type": "title",
            "title": [
                {
                    "type": "text",
                    "text": {
                        "content": "LOLLL",
                        "link": None
                    },
                    "annotations": {
                        "bold": False,
                        "italic": False,
                        "strikethrough": False,
                        "underline": False,
                        "code": False,
                        "color": "default"
                    },
                    "plain_text": "10",
                    "href": None
                }
            ]
        }
    },



    }
    response = requests.post(url, headers=headers, json=payload)
    print(response.json())
    return response


async def save_to_notion(user_id, context):
    coach = MULTI_TAGS["coach"][sessions[user_id]["coach"]]
    type = MULTI_TAGS["type"][sessions[user_id]["type"].capitalize()]
    print(f"coach: {coach}, type: {type}")
#    data = sessions[user_id]
#    data = json.loads(open('data', 'r').read())
    # with open('data' , 'w') as myf:
    #     myf.write(json.dumps(data))
#    exercises_text = "\n\n".join([f"**{ex['type']}**\n{ex['description']}"
    #    for ex in sessions[user_id]['exercises']])
    date_str = datetime.now().isoformat()
    url = 'https://api.notion.com/v1/pages'
    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Content-Type': 'application/json',
        'Notion-Version': '2021-05-13'
    }
    payload = {
    'parent': {'database_id': NOTION_DATABASE_ID},
    "object": "page",
    "last_edited_time": datetime.now().isoformat(),
    "created_by": {
        "object": "user",
        "id": "33f7619f-8330-4fb9-9889-706bcd9b6a01"
    },
    "last_edited_by": {
        "object": "user",
        "id": "33f7619f-8330-4fb9-9889-706bcd9b6a01"
    },
    "cover": None,
    "icon": None,
    "parent": {
        "type": "database_id",
        "database_id": "0f05bd21-7122-4d20-af9b-b9b6cdaa2654"
    },
    "archived": False,
    "in_trash": False,
    "properties": {
        "Coach": {
            "id": "aYm;",
            "type": "select",
            "select": {
                "id": coach["id"],
                "name":coach["name"],
                "color": coach["color"],
                "description": None
            }
        },
        "Tags": {
            "id": "bqtJ",
            "type": "multi_select",
            "multi_select": [
                {
                    "id": type["id"],
                    "name":type["name"],
                    "color": type["color"]
                }
            ]
        },
        "AI summary": {
            "id": "n<mr",
            "type": "rich_text",
            "rich_text": []
        },
        "Date": {
            "id": "}DM<",
            "type": "date",
            "date": {
                "start": datetime.now().isoformat(),
                "end": None,
                "time_zone": None
            }
        },
        "Name": {
            "id": "title",
            "type": "title",
            "title": [
                {
                    "type": "text",
                    "text": {
                        "content": "LOL",
                        "link": None
                    },
                    "annotations": {
                        "bold": False,
                        "italic": False,
                        "strikethrough": False,
                        "underline": False,
                        "code": False,
                        "color": "default"
                    },
                    "plain_text": "10",
                    "href": None
                }
            ]
        }
    },
            }        
    
    response = requests.post(url, headers=headers, json=payload)
    response_data = response.json()
    print(response_data)
    return response_data["id"]


def test():
    url = 'https://api.notion.com/v1/pages/f230b3b1e5c0410aa7f6d174f2cdabec'
    print(url)
    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Content-Type': 'application/json',
        'Notion-Version': '2021-05-13'
    }
    response = requests.get(url, headers=headers)
    with open('page', 'w') as f:
        f.write(response.text)
    print(response.json())

# async def append_block_to_page(page_id, user_id):
async def append_block_to_page(page_id, user_id):
    data = sessions[user_id]
    # exercises_text = "\n\n".join([f"**{ex['type']}**\n{ex['description']}" for ex in data['exercises']])
    # with open('page-data', 'w') as d:
    #     d.write(json.dumps(data))
    print(f"APPENDING!")
    # data = json.loads(open('page-data', 'r').read())
    blocks = []

    for exercise in data['exercises']:
        blocks.append({
            'object': 'block',
            'type': 'paragraph',
            'paragraph': {
                'rich_text': [
                    {
                        'type': 'text',
                        'text': {
                            'content': exercise['type'],
                        },
                        'annotations': {
                            'bold': True
                        }
                    },
                    {
                        'type': 'text',
                        'text': {
                            'content': f"\n{exercise['description']}\n"
                        }
                    }
                ]
            }
        })

    if 'custom_exercises' in data:
        for custom_exercise in data['custom_exercises']:
            blocks.append({
                'object': 'block',
                'type': 'paragraph',
                'paragraph': {
                    'rich_text': [
                        {
                            'type': 'text',
                            'text': {
                                'content': custom_exercise['type'],
                            },
                            'annotations': {
                                'bold': True
                            }
                        },
                        {
                            'type': 'text',
                            'text': {
                                'content': f"\n"
                                           f""
                                           f"{custom_exercise['description']}\n"
                            }
                        }
                    ]
                }
            })

    url = f'https://api.notion.com/v1/blocks/{page_id}/children'
    headers = {
        'Authorization': f'Bearer {NOTION_TOKEN}',
        'Content-Type': 'application/json',
        'Notion-Version': '2022-06-28'  # Ensure you're using the latest version
    }
    payload = {
        'children': blocks
    }

    response = requests.patch(url, headers=headers, json=payload)
    response_data = response.json()
    print(response_data)
    response.raise_for_status()  # Raise an error for bad responses
    return response_data



def main():
    # append_block_to_page("3a759b0b439f417b847fc20e3d6e0306",USER_ID)
    #testme()
    #test()
    application = Application.builder().token(TELEGRAM_TOKEN).build()
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', new_log)],
        states={
            CHOOSING_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_type)],
            CHOOSING_COACH: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_coach)],
            COLLECTING_DESCRIPTIONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, collect_description)],
            ADDING_CUSTOM_EXERCISE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_custom_exercise)],
            ADDING_CUSTOM_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_custom_description)]
        },
        fallbacks=[CommandHandler('stop', stop)],
    )
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("status", view_status))  # Add this line
    application.run_polling()


if __name__ == '__main__':
    main()

