from datetime import datetime
from typing import List, Optional
from src.memory import Memory, Message, Channel, MemoryCell
from keys import openrouter_free as API_KEY
from src.llm import send_stream_request
import prompts
import json
from humanize import naturaltime
import time
from src import utils
import discord
import ijson
from typing import AsyncIterator


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

    async def process_message_stream(self, new_msg: Message, message_discord: discord.Message | None = None):
        if not self.current_channel:
            raise ValueError("Channel not selected!")
        
        full_sequence = []
        buffer = ""
        tasks_was = []

        async for chunk in self._get_stream_response(new_msg, message_discord):
            for ch in chunk:
                buffer += ch
                buffer = buffer.removeprefix("```json\n").removesuffix("\n```")
                post_processed_buffer = buffer + "\n  ]\n}" if not buffer.endswith("\n  ]\n}") else buffer
                try:
                    tasks = json.loads(post_processed_buffer).get("action_sequence")
                    for i in range(len(tasks)):
                        if i in tasks_was:
                            continue
                        tasks_was.append(i)
                        yield tasks[i]
                    
                except json.JSONDecodeError:
                    continue

    async def _get_stream_response(
        self, 
        new_msg: Message, 
        message_discord: discord.Message
    ) -> AsyncIterator[str]:
        
        # Сообщения на отправку
        messages = [{"role": "system", "content": prompts.system_sequence_logic_v2}]

        # Получаем историю сообщений
        context = [
            {
                "author": msg.author.replace("Alpha", "Alpha (ты)"),
                "content": msg.text,
                "relative_time": naturaltime(datetime.now() - datetime.fromtimestamp(msg.timestamp)),
                "id": msg.id,
                "meta-information": msg.metainfo
            }
            for msg in self.memory.get_messages(self.current_channel)
        ]


        prompt_dict = {
            "Память": {},
            "time_now": time.strftime("%Y %B %d %H:%M:%S", time.localtime(new_msg.timestamp))
        }
        prompt_memory = {}
        for topic in self.memory.get_memory().keys():
            prompt_memory[topic] = [
                {
                    "id": cell.id,
                    "content": cell.text,
                    "last_time_updated": naturaltime(datetime.now() - datetime.fromtimestamp(cell.timestamp))
                } for cell in self.memory.get_memory()[topic]
            ]
        
        new_msg_prompt = {
            "new_message_id": new_msg.id,
            "author": new_msg.author,
            "content": new_msg.text,
            "meta-information": new_msg.metainfo
        }

        #for topic in prompt_dict["Память"].keys():
        #    for i in range(len(prompt_dict["Память"][topic])):
        #        prompt_dict["Память"][topic][i]["last_time_updated"] = naturaltime(datetime.now() - datetime.fromtimestamp(prompt_dict["Память"][topic][i]["timestamp"]))
        #        prompt_dict["Память"][topic][i].pop("timestamp")


        messages.append(
                {
                    "role": "user",
                    "content": "```json\n" + prompts.user + "Твоя память:\n" + self.preprocess(json.dumps(prompt_memory, ensure_ascii=False, indent=2), message_discord) + "\n```\n**ВАЖНО УЧИТЫВАТЬ ВСЮ ПАМЯТЬ!!! НЕ ЗАБУДЬ НИ ОДНУ ЗАПИСЬ!**"
                }
        )
        messages.append({"role": "assistant", "content": "Хорошо, все эти записи будут учтены! Я ничего не забуду."})
        messages.append(
                {
                    "role": "user",
                    "content": "```json\n" + prompts.user + "История сообщений:\n" + self.preprocess(json.dumps(context, ensure_ascii=False, indent=2), message_discord) + "\n```\n**НЕ ПОВТОРЯЙ СООБЩЕНИЯ, КОТОРЫЕ УЖЕ ОТПРАВЛЯЛА**\nВ следующем сообщении отправь только json!!!"
                }
        )
        messages.append({"role": "assistant", "content": "Отлично, я буду учитывать эту историю сообщений, чтобы ответить максимально соответствующе. Так же я буду стараться не повторять сообщения, которые уже задавала."})
        messages.append(
                {
                    "role": "user",
                    "content": "```json\n" + prompts.user + self.preprocess(json.dumps(new_msg_prompt, ensure_ascii=False, indent=2), message_discord) + "\n```\nP.S. Используй функции, которые тебе известны, на максимум. Запоминай, изменяй, общайся, использу задержку чтобы казаться естественнее. Не отправляй слишком длинный send_message. Лучше разделить на несколько действий с задержками между ними.\n#### **ОПИРАЙСЯ НА СВОИ ВОСПОМИНАНИЯ ПРИ ОТВЕТЕ**\n#### **СЛЕДИ, ЗАПОМИНАЙ, УДАЛЯЙ И ИЗМЕНЯЙ ВОСПОМИНАНИЯ, ЧТОБЫ СДЕЛАТЬ ИХ АККУРАТНЕЕ, ПОНЯТНЕЕ И ЭФФЕКТИВНЕЕ ВНЕ ЗАВИСИМОСТИ ОТ КОНТЕКСТА**\nРасписывай action_sequence на час вперед. Если люди не будут писать долгое время, то action_sequence продолжит свое выполнение."
                }
        )
        messages.append({"role": "assistant", "content": "```json\n"})

        # Добавляем в память
        self.memory.add_message(self.current_channel, new_msg)

        dynamic_prompt = json.dumps(messages, ensure_ascii=False, indent=2)
        for msg in messages:
            print(json.dumps(msg, ensure_ascii=False, indent=2))
        
        async for chunk in send_stream_request(messages, API_KEY):
            yield chunk
    
    def preprocess(self, text: str, message: discord.Message | None = None):
        return utils.replace_mentions_with_nicks(text, message) if message else text

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