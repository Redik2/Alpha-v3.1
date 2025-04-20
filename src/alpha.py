from datetime import datetime
from typing import List, Optional
from src.memory import Memory, Message, Channel, Note
from keys import openrouter_free as API_KEY
from src.llm import send_request
import prompts
import json
from humanize import naturaltime

class Alpha:
    def __init__(self, memory_file: str = "alpha_memory.json"):
        self.memory = Memory(memory_file)
        self.current_channel: Optional[Channel] = None

    def set_channel(self, channel_type: int, channel_id: int) -> None:
        """Установить текущий канал для работы"""
        self.current_channel = self.memory.find_channel(channel_type, channel_id)
        if not self.current_channel:
            self.current_channel = Channel(channel_type, channel_id)
            self.memory.add_channel(self.current_channel)

    def process_message(self, text: str, author: str = "user") -> dict:
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

        # Получаем историю сообщений
        context = [
            {"author": msg.author, "content": msg.text, "timestamp": naturaltime(datetime.now() - datetime.fromtimestamp(msg.timestamp)), "timestamp_iso": str(datetime.fromtimestamp(msg.timestamp))}
            for msg in self.memory.get_messages(self.current_channel)
        ]


        prompt_dict = {"message_history": context, "your_notes": [note.to_dict() for note in self.memory.get_notes()], "author": new_msg.author, "content": new_msg.text, "time_now": str(datetime.fromtimestamp(new_msg.timestamp))}

        for i in range(len(prompt_dict["your_notes"])):
            prompt_dict["your_notes"][i]["timestamp"] = naturaltime(datetime.now() - datetime.fromtimestamp(prompt_dict["your_notes"][i]["timestamp"]))

        dynamic_prompt = json.dumps(prompt_dict, ensure_ascii=False, indent=2)
        print(dynamic_prompt)


        messages.append({"role": "user", "content": "```json\n" + prompts.user + dynamic_prompt + "\n```"})
        
        # Добавляем в память
        self.memory.add_message(self.current_channel, new_msg)

        # Отправляем запрос к LLM
        #print(json.dumps(messages, indent=2, ensure_ascii=False))
        response = send_request(messages, API_KEY).strip().removeprefix("```json\n").removesuffix("\n```")
        print("Response:")
        print(response)
        response = json.loads(response)

        # Создаем объект сообщения
        if not response["message_sequence"][0]:
            return None
        new_msg = Message(
            timestamp=datetime.now().timestamp(),
            text=response["message_sequence"][0]["content"],
            author="Alpha"
        )

        # Добавляем в память
        #self.memory.add_message(self.current_channel, new_msg)

        new_notes = response["new_notes_or_edit_notes"]
        for note in new_notes:
            self.memory.add_note(Note(
                timestamp=datetime.now().timestamp(),
                text=note["content"],
                id=note["id"]
            ))
        
        for id in response["remove_notes"]:
            self.memory.remove_note(id)
        
        self.save_memory()

        # Обрабатываем ответ
        return self._handle_response(response)

    def _handle_response(self, response: str) -> str:
        """Обработка ответа от LLM, выполнение команд"""
        if not response:
            return None
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