from datetime import datetime
from typing import List, Optional
from src.memory import Memory, Message, Channel
from keys import openrouter_free as API_KEY
from src.llm import send_request
import prompts
import json

class Alpha:
    def __init__(self, memory_file: str = "alpha_memory.json"):
        self.memory = Memory(memory_file)
        self.current_channel: Optional[Channel] = None

    def set_channel(self, channel_type: int, channel_id: int) -> None:
        """Установить текущий канал для работы"""
        self.current_channel = Channel(channel_type, channel_id)
        self.memory.add_channel(self.current_channel)

    def process_message(self, text: str, author: str = "user") -> str:
        """Основной метод для обработки входящего сообщения"""
        if not self.current_channel:
            raise ValueError("Channel not selected!")
        
        # Создаем объект сообщения
        new_msg = Message(
            timestamp=datetime.now().timestamp(),
            text=text,
            author=author
        )
        
        
        # Сообщения на отправку
        messages = [{"role": "system", "content": prompts.system}]

        dynamic_prompt = ""

        # Получаем историю сообщений
        history = [
            {"author": msg.author, "content": msg.text, "timestamp": str(datetime.fromtimestamp(msg.timestamp))}
            for msg in self.memory.get_messages(self.current_channel)
        ]

        prompt_dict = {"chat_id": f"{self.current_channel.type}{self.current_channel.id}", "author": new_msg.author, "content": new_msg.text, "time_now": str(datetime.fromtimestamp(new_msg.timestamp)), "context": history}

        dynamic_prompt = json.dumps(prompt_dict, indent=4, ensure_ascii=False)


        messages.append({"role": "user", "content": "```json\n" + prompts.user + dynamic_prompt + "\n```"})
        
        # Добавляем в память
        self.memory.add_message(self.current_channel, new_msg)

        # Отправляем запрос к LLM
        print(json.dumps(messages, indent=4, ensure_ascii=False))
        response = send_request(messages, API_KEY).strip().removeprefix("```json\n").removesuffix("\n```")
        print(response)
        response = json.loads(response)

        # Создаем объект сообщения
        new_msg = Message(
            timestamp=datetime.now().timestamp(),
            text=response["content"],
            author="Alpha"
        )

        # Добавляем в память
        self.memory.add_message(self.current_channel, new_msg)
        
        # Обрабатываем ответ
        return self._handle_response(response["content"])

    def _handle_response(self, response: str) -> str:
        """Обработка ответа от LLM, выполнение команд"""
        if not response:
            return None
        if response.startswith("!"):
            return self._execute_command(response)
        return response

    def _execute_command(self, command: str) -> str:
        """Выполнение системных команд"""
        # Здесь должна быть ваша логика выполнения команд
        # Пример:
        try:
            pass
        
        except Exception as e:
            return f"Ошибка выполнения команды: {str(e)}"

    def save_memory(self) -> None:
        """Сохранение памяти на диск"""
        self.memory.save()