# Gymnaskillazy - a [Lazy] Gym Bot
<img src="logo.png" alt="Logo" width="300"/>


## Overview
The **Gymnaskillazy** is an intelligent bot that logs exercises and lessons to Notion based on user inputs from Telegram. It uses Google Sheets to manage exercises and additional questions, and leverages OpenAI's GPT-4 model to generate lesson titles. The bot is hosted on AWS Lambda for cost efficiency and scalability, but mainly because I'm lazy.
<br><br>
[![See the demo](https://cdn-images-1.medium.com/max/2400/1*knREUqTS5Gh5JA3qt4505Q.png)](https://youtu.be/5U-fgv25d-k)
<br>
[See the demo](https://youtu.be/5U-fgv25d-k)

## Why like that
Using existing (Zapier-like) tools costs money, limited and is much less fun than having the ups & downs of developing a system from scratch.
Also - I got pretty bored this weekend.

## Features
- **Exercise Logging**: Logs exercises and lessons with descriptions to Notion.
- **Google Sheets Integration**: Fetches exercises and additional questions from Google Sheets.
- **AI-Generated Titles**: Uses OpenAI GPT-4 to generate concise and meaningful lesson titles.
- **AWS Lambda Hosting**: Runs on AWS Lambda, triggered by webhooks, and uses CloudWatch for scheduling.

## Components
1. Telegram Bot - Handles user interactions, collects exercise details, and communicates with other components.
2. Google Sheets Client- Fetches exercise data and additional questions from Google Sheets.
3. Notion Client - Saves the collected data to a Notion database.
4. OpenAI Client - Generates lesson titles based on the logged exercises.
5. AWS Lambda - Hosts the bot and handles incoming webhook requests from Telegram.


## Setup Instructions

### Prerequisites

- **Python 3.12**
- **Poetry** for dependency management
- **AWS CLI** configured with your AWS credentials
- **AWS Lambda** and **API Gateway** setup

### Environment Variables

Create a `.env` file in the root directory with the following keys:

```dotenv
TELEGRAM_TOKEN=<Your_Telegram_Bot_Token>
NOTION_TOKEN=<Your_Notion_Integration_Token>
NOTION_DATABASE_ID=<Your_Notion_Database_ID>
GOOGLE_SHEETS_CREDENTIALS_FILE=credentials.json
GOOGLE_SHEETS_ID=<Your_Google_Sheets_ID>
OPENAI_API_KEY=<Your_OpenAI_API_Key>
TELEGRAM_USER_ID=<Your_Telegram_User_ID>
NOTION_USER_ID=<Your_Notion_User_ID>
WEBHOOK_URL=<Your_Webhook_URL> # URL to be set for webhook
SECRET_TOKEN=<Your_Secret_Token> # Token to secure webhook - optional! (or not? ;))
TELEGRAM_USER_ID=<Your user ID in telegram> 
NOTION_USER_ID=<Your user ID in Notion> 
```

### Google Sheets Setup

1. Create a Google Sheet with tabs named after the months (e.g., July, August) and one tab named `General`.
2. Add your exercises to the respective monthly tabs and questions to the `General` tab.
3. Share the Google Sheet with the service account email from your `credentials.json`.

### Notion Setup

1. Create a database in Notion and note its ID.
2. Configure an integration in Notion and add it to the database.

### Installation

1. **Clone the repository:**
   ```sh
   git clone <repository-url>
   cd telegram-notion-bot
    ```

2. **Install dependencies using Poetry:**
Inside root, with your virtual env activated, run
```sh 
poetry install --no-root
```

3. ** Optional: Deploy to AWS Lambda:**

Zip your project files and dependencies.
Upload the zip file to AWS Lambda.
Set up API Gateway to trigger the Lambda function.
Configure the webhook for the Telegram bot to point to your API Gateway endpoint. - note the `set_webhook` function in _bot.py_

### Running the Bot
- Offline (Polling Mode): The bot runs locally and polls for new messages.
- Online (Webhook Mode): The bot is triggered by webhooks when new messages arrive.


### Example Usage
Start the bot by sending the /start command in Telegram.
Follow the prompts to log your exercises and answer additional questions.
The bot will save the data to Notion and generate a lesson title using OpenAI GPT-4.

Good luck!