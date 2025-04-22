import aiohttp
import json
from typing import AsyncIterator

async def send_stream_request(
    messages: list[dict], 
    key: str
) -> AsyncIterator[str]:
    """
    Выполняет POST-запрос с stream=True и построчно отдаёт
    блоки контента ('content') из SSE-ответа.
    """
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://localhost",
        "X-Title": "Alpha v3"
    }
    payload = {
        "model": "deepseek/deepseek-chat:free",
        "temperature": 0.4,
        "messages": messages,
        "stream": True,
        "provider": {"sort": "latency"}
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            # Читаем ответ построчно
            async for raw_line in resp.content:
                line = raw_line.decode('utf-8').strip()
                # Игнорируем всё, что не начинается с "data: "
                if not line.startswith("data: "):
                    continue

                data_str = line[len("data: "):]
                # Конец стрима
                if data_str == "[DONE]":
                    break

                try:
                    msg = json.loads(data_str)
                    delta = msg["choices"][0].get("delta", {})
                except (json.JSONDecodeError, KeyError):
                    continue

                # Если в дельте есть контент — отдаём его как следующий кусок
                if content := delta.get("content"):
                    yield content
