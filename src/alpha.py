from datetime import datetime
from typing import List, Optional
from src.memory import Memory, Message, Channel, MemoryCell
from keys import openrouter_free as API_KEY
from src.llm import send_request
import prompts
import json
from humanize import naturaltime
import time
from src import utils
import discord


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

    def add_startup_message(self) -> bool:
        if not self.current_channel:
            return False
        new_msg = Message(
            timestamp=datetime.now().timestamp(),
            text="Только что ты была включена или перезагружена. Если до этого нет сообщений о выключении, значит это внеплановая перезагрузка, вероятнее всего вызванная ошибкой",
            author="system"
        )
        self.memory.add_message(self.current_channel, new_msg)
        self.memory.save()
        return True

    def add_shutdown_message(self) -> bool:
        if not self.current_channel:
            return False
        new_msg = Message(
            timestamp=datetime.now().timestamp(),
            text="Только что ты была выключена(естественным способом, без ошибок)",
            author="system"
        )
        self.memory.add_message(self.current_channel, new_msg)
        self.memory.save()
        return True

    def add_error_message(self) -> bool:
        if not self.current_channel:
            return False
        new_msg = Message(
            timestamp=datetime.now().timestamp(),
            text="Только что ты была выключена(из за возникновения неизвестной ошибки в коде)",
            author="system"
        )
        self.memory.add_message(self.current_channel, new_msg)
        self.memory.save()
        return True

    def add_clear_history_message(self) -> bool:
        if not self.current_channel:
            return False
        new_msg = Message(
            timestamp=datetime.now().timestamp(),
            text="Только что все сообщения в чате были стерты(по прозьбе создателя)",
            author="system"
        )
        self.memory.add_message(self.current_channel, new_msg)
        self.memory.save()
        return True

    def process_message(self, new_msg: Message, message_discord: discord.Message | None = None) -> dict:
        """Основной метод для обработки входящего сообщения"""
        if not self.current_channel:
            raise ValueError("Channel not selected!")
        
        
        # Сообщения на отправку
        messages = [{"role": "system", "content": prompts.system_sequence_logic_v2}]

        # Получаем историю сообщений
        context = [
            {
                "author": msg.author.replace("Alpha", "Alpha (ты)"),
                "content": msg.text,
                "relative_time": naturaltime(datetime.now() - datetime.fromtimestamp(msg.timestamp)),
                "id": msg.id
            }
            for msg in self.memory.get_messages(self.current_channel)
        ]


        prompt_dict = {
            "Память": {},
            "message_history": context,
            "new_message_id": new_msg.id,
            "author": new_msg.author, "content": new_msg.text,
            "time_now": time.strftime("%Y %B %d %H:%M:%S", time.localtime(new_msg.timestamp))
        }
        for topic in self.memory.get_memory().keys():
            prompt_dict["Память"][topic] = "\n".join([f"{cell.id}: {cell.text} ({naturaltime(datetime.now() - datetime.fromtimestamp(cell.timestamp))})" for cell in self.memory.get_memory()[topic]])

        #for topic in prompt_dict["Память"].keys():
        #    for i in range(len(prompt_dict["Память"][topic])):
        #        prompt_dict["Память"][topic][i]["last_time_updated"] = naturaltime(datetime.now() - datetime.fromtimestamp(prompt_dict["Память"][topic][i]["timestamp"]))
        #        prompt_dict["Память"][topic][i].pop("timestamp")
        

        dynamic_prompt = json.dumps(prompt_dict, ensure_ascii=False, indent=2)
        print(dynamic_prompt)


        messages.append({"role": "user", "content": "```json\n" + prompts.user + utils.replace_mentions_with_nicks(dynamic_prompt, message_discord) if message_discord else dynamic_prompt + "\n```"})
        
        # Добавляем в память
        self.memory.add_message(self.current_channel, new_msg)

        # Отправляем запрос к LLM
        #print(json.dumps(messages, indent=2, ensure_ascii=False))
        response = send_request(messages, API_KEY).strip().removeprefix("```json\n").removesuffix("\n```")
        print("Response:")
        print(response)
        response = json.loads(response)
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
    
    def clear_current_channel(self) -> bool:
        if not self.current_channel:
            return False
        self.memory.clear_channel(self.current_channel)
        self.add_clear_history_message()
        self.memory.save()
        return True
    
    def clear_notes(self) -> bool:
        for note in self.memory.get_notes():
            self.memory.remove_note(note.id)
        self.add_clear_notes_message()
        self.memory.save()
        return True