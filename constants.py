EXPLANATIONS_TEXT = ("In every step you can write "
                     "'skip' - skip logging that specific exercise\n"
                     "'add' - add a custom exercise\n"
                     "'end' - finish logging - save to notion\n")

MULTI_TAGS = {
    "coach": {
        "Alon": {
            "id": "h\\I[",
            "color": "brown",
            "name": "Alon",
            "description": None
        },
        "Yair": {
            "id": "oR:g",
            "name": "Yair",
            "color": "blue",
            "description": None
        },
        "Sagi": {
            "id": "aw?v",
            "name": "Sagi",
            "color": "orange",
            "description": None
        },
        "Shahar": {
            "id": "dmi[",
            "name": "Shahar",
            "color": "yellow",
            "description": None
        },
        "Carmel": {
            "id": "86997e0c-075e-4732-ae6d-3df42db11cbe",
            "name": "Carmel",
            "color": "red",
            "description": None
        }
    },
    "type": {
        "Strength": {
            "id": "cd94d728-3bb9-4895-bf9c-43ca23505b72",
            "name": "Strength",
            "color": "purple",
            "description": None
        },
        "Skill": {
            "id": "2b0b454b-6f37-4a5c-858f-e69732c58b5d",
            "name": "Skill",
            "color": "green",
            "description": None
        },
        "Range": {
            "id": "8d0ec6ef-fe7a-42d1-bb93-ae8e5a02d5ed",
            "name": "Range",
            "color": "yellow",
            "description": None
        },
        "Handstand": {
            "id": "63bcb531-ce54-40c5-a83b-48258c45f628",
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

