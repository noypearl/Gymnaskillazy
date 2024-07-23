# GOOGLE SHEETS NAMES

GENERAL_SHEET = "General"
TRAINERS_COL = "Trainers"
QUESTIONS_COL = "Questions"
EXERCISE_SHEET = "Exercise List"
EXERCISE_ID_COL = "Exercise ID"
CURRENT_COL = "Current"
USERS_SHEET = "Users"
LOG_SHEET = "Full Workout Log"


# TODO: ADD COMMANDS (END,START,SKIP...)

EXPLANATIONS_TEXT = ("In every step you can write "
                     "'skip' - skip logging that specific exercise\n"
                     "'add' - add a custom exercise\n"
                     "'end' - finish logging - save to notion\n")

MULTI_TAGS = {
    "coach": {
        "Alon": {
            "id": ">@\\p",
            "name": "Alon",
            "color": "green",
            "description": None
        },
        "Yair": {
            "id": "Lb@:",
            "name": "Yair",
            "color": "default",
            "description": None
        },
        "Sagi": {
            "id": "}cYR",
            "name": "Sagi",
            "color": "red",
            "description": None
        },
        "Shahar": {
            "id": "FglX",
            "name": "Shahar",
            "color": "brown",
            "description": None
        }
    },
    "type": {
        "Strength": {
            "id": "EL\\u",
            "name": "Strength",
            "color": "purple",
            "description": None
        },
        "Skill": {
            "id": "DVho",
            "name": "Skill",
            "color": "green",
            "description": None
        },
        "Range": {
            "id": "v^]a",
            "name": "Range",
            "color": "yellow",
            "description": None
        },
        "Handstand": {
            "id": "u<ga",
            "name": "Handstand",
            "color": "orange",
            "description": None
        }
    }
}
CHATGPT_PROMPT = "I have json of gym exercises that I logged. It holds " \
                  "key for exercise type and value for the description. " \
                  "Also it has additional questions. I want to analyze " \
                  "it and create a short title of the exercise - put a colon between exercises instead of words. use minimum words. remove words such as 'seconds' and instead keep the number only. It should be one line only. no newlines. Don't tell me the training type. Don't tell me the coach. Don't tell me the goal. I want to know about the big achievements. minimum words. no more than 10 words Don't mention the word 'title'. here it is: "

