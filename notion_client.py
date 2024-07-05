import requests
import json
from datetime import datetime
from constants import MULTI_TAGS, NOTION_USER_ID
import logging

class NotionClient:
    def __init__(self, notion_token, notion_database_id):
        self.notion_token = notion_token
        self.notion_database_id = notion_database_id
        self.headers = {
            'Authorization': f'Bearer {self.notion_token}',
            'Content-Type': 'application/json',
            'Notion-Version': '2022-06-28'
        }
        self.logger = logging.getLogger(__name__)

    async def save_to_notion(self, user_id, lesson_title, lesson_index, sessions):
        coach = MULTI_TAGS["coach"][sessions[user_id]["coach"]]
        type_tag = MULTI_TAGS["type"][sessions[user_id]["type"].capitalize()]
        user_id = NOTION_USER_ID  # TODO - get user ID from notion connection
        self.logger.info(f"Saving lesson for user {user_id} to Notion with coach {coach['name']} and type {type_tag['name']}")

        date_str = datetime.now().isoformat()
        url = 'https://api.notion.com/v1/pages'
        payload = {
            'parent': {'database_id': self.notion_database_id},
            "object": "page",
            "last_edited_time": datetime.now().isoformat(),
            "created_by": {
                "object": "user",
                "id": user_id
            },
            "last_edited_by": {
                "object": "user",
                "id": user_id
            },
            "properties": {
                "Coach": {
                    "id": "aYm;",
                    "type": "select",
                    "select": {
                        "id": coach["id"],
                        "name": coach["name"],
                        "color": coach["color"],
                        "description": coach["description"]
                    }
                },
                "Tags": {
                    "id": "bqtJ",
                    "type": "multi_select",
                    "multi_select": [
                        {
                            "id": type_tag["id"],
                            "name": type_tag["name"],
                            "color": type_tag["color"]
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
                        "start": date_str,
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
                                "content": lesson_title,
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
                            "plain_text": lesson_title,
                            "href": None
                        }
                    ]
                }
            }
        }

        response = requests.post(url, headers=self.headers, json=payload)
        response_data = response.json()
        print(response_data)
        self.logger.info(f"Response from Notion: {response_data}")
        response.raise_for_status()
        return response_data["id"]

    async def append_block_to_page(self, page_id, data):
        blocks = []
        with open('data', 'w') as f:
            f.write(json.dumps(data))
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
                                    'content': f"\n{custom_exercise['description']}\n"
                                }
                            }
                        ]
                    }
                })

        if 'additional_info' in data:
            for item in data['additional_info']:
                blocks.append({
                    'object': 'block',
                    'type': 'paragraph',
                    'paragraph': {
                        'rich_text': [
                            {
                                'type': 'text',
                                'text': {
                                    'content': item['question'],
                                },
                                'annotations': {
                                    'bold': True
                                }
                            },
                            {
                                'type': 'text',
                                'text': {
                                    'content': f"\n{item['answer']}\n"
                                }
                            }
                        ]
                    }
                })

        url = f'https://api.notion.com/v1/blocks/{page_id}/children'
        payload = {'children': blocks}

        response = requests.patch(url, headers=self.headers, json=payload)
        response_data = response.json()
        self.logger.info(f"Appended blocks to Notion page {page_id}: {response_data}")
        response.raise_for_status()
        return response_data
