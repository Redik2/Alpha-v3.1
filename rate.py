import requests
import json
from keys import openrouter as key

response = requests.get(
  url="https://openrouter.ai/api/v1/auth/key",
  headers={
    "Authorization": f"Bearer {key}"
  }
)

print(json.dumps(response.json(), indent=2))
