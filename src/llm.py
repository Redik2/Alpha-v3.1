import json
import requests

def send_request(messages: list, key: str) -> str:
    try:
        response = None
        for i in range(10):
            try:
                response = requests.post(
                url="https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://localhost",
                    "X-Title": "Alpha v3"
                },
                data=json.dumps({
                    "models": [
                        "deepseek/deepseek-chat:free",
                        "deepseek/deepseek-chat-v3-0324:free",
                        "deepseek/deepseek-v3-base:free"
                    ],
                    "temperature": 0.6,
                    "messages": messages
                }), timeout=40
                )
            except requests.Timeout:
                response = None
            if response:
                return response.json()["choices"][0]["message"]["content"]
            
            return response.json()["choices"][0]["message"]["content"]
        raise requests.Timeout
    except Exception as e:
        print("Error!")
        print("Request:\n" + response.request.body)
        print("Response:\n" + str(response.json()))
        raise e