import json
import requests

def send_request(messages: list, key: str) -> str:
    response = requests.post(
    url="https://openrouter.ai/api/v1/chat/completions",
    headers={
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://localhost",
        "X-Title": "Alpha v3"
    },
    data=json.dumps({
        "model": "deepseek/deepseek-chat-v3-0324:free",
        "temperature": 0.8,
        "messages": messages
    })
    )
    try:
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        print("Error!")
        print("Request:\n" + response.request.body)
        print("Response:\n" + response.json())
        raise e