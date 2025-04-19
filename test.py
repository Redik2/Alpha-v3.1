import requests
import json
from keys import openrouter_free as key
import prompts

response = requests.post(
  url="https://openrouter.ai/api/v1/chat/completions",
  headers={
    "Authorization": f"Bearer {key}",
    "Content-Type": "application/json",
    "HTTP-Referer": "https://localhost",
    "X-Title": "Alpha v3"
  },
  data=json.dumps({
    "model": "deepseek/deepseek-v3-base:free",
    "temperature": 0.8,
    "messages": [
        {
            "role": "system",
            "content": prompts.test
        },
        {
            "role": "user",
            "content": "DVD314: Привет, Альфа"
        },
        { 
            "role": 'assistant',
            "content": "Alpha: "
        }
    ]
  })
)

print(response.json())