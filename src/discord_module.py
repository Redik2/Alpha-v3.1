import discord
import asyncio
import json
from datetime import datetime
from typing import Optional, Dict
from discord.ext import commands
from src.alpha import Alpha
from src.memory import ChannelTypes, Message, MemoryCell
from keys import discord_token
import random
import src.utils as utils


CHANNEL_ID = 828610429897932813


class DiscordBot:
    def __init__(self, alpha: Alpha):
        self.token = discord_token
        self.alpha = alpha
        self.bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
        self.queues: Dict[int, asyncio.Queue] = {}  # Очереди задач по каналам
        self.processors: Dict[int, asyncio.Task] = {}  # Активные обработчики очередей
        self.active_tasks: Dict[int, asyncio.Task] = {}
        
        self.alpha.set_channel(ChannelTypes.discord, CHANNEL_ID)

        # Регистрация обработчиков событий
        self.bot.add_listener(self.on_ready)
        self.bot.add_listener(self.on_message)

    async def sequence_process(self, message: discord.Message, task: dict):
        """Отправляет сообщения с задержками с возможностью прерывания"""
        channel = message.channel
        try:
            match task["action_name"]:
                case "send_message":
                    typing_time = len(task["content"]) * 0.04 * (0.75 + random.random() * 0.5)
                    async with channel.typing():
                        await asyncio.sleep(typing_time)
                        content = utils.replace_nicks_with_mentions(task["content"], message)
                        metainfo = {}

                        if not "reply_message_id" in task.keys():
                            new_msg = await channel.send(content)
                        else:
                            msg = await channel.fetch_message(task["reply_message_id"])
                            new_msg = await msg.reply(content)
                            metainfo["reply_message_id"] = task["reply_message_id"]
                        
                        self.alpha.memory.add_message(self.alpha.current_channel,
                                                    Message(
                            timestamp=datetime.now().timestamp(),
                            text=content,
                            author="Alpha",
                            id=new_msg.id,
                            metainfo=metainfo
                        ))
                case "edit_message":
                    msg = await channel.fetch_message(task["message_id"])
                    new_content = task["new_content"]
                    await msg.edit(content=new_content)
                    msg = self.alpha.memory.find_message(self.alpha.current_channel, task["message_id"])
                    msg.text = new_content
                    msg.metainfo["edited"] = True

                case "wait":
                    await asyncio.sleep(float(task["seconds"]))
                case "remember":
                    new_memory = MemoryCell(
                            timestamp = datetime.now().timestamp(),
                            text = task["content"],
                            id = utils.generate_id() if not "id" in task.keys() or not task["id"] else task["id"]
                    )
                    self.alpha.memory.add_memory(topic=task["topic"], memory=new_memory)
                case "forget":
                    self.alpha.memory.remove_memory(task["topic"], task["id"])
                case "modify_memory":
                    new_memory = MemoryCell(
                            timestamp = datetime.now().timestamp(),
                            text = task["content"],
                            id = task["id"]
                    )
                case "add_reaction_emoji_icon":
                    try:
                        msg = await channel.fetch_message(task['message_id'])
                    except:
                        pass
                    await msg.add_reaction(task['emoji'])
                    msg = self.alpha.memory.find_message(self.alpha.current_channel, task["message_id"])
                    msg.metainfo["you_placed_reaction_icon"] = task['emoji']
            self.alpha.memory.save()
        except asyncio.CancelledError:
            return

    async def queue_processor(self, channel_id: int):
        """Асинхронно обрабатывает очередь задач для канала"""
        while True:
            try:
                # Ждем новую задачу с таймаутом для возможности завершения
                task = await asyncio.wait_for(
                    self.queues[channel_id].get(),
                    timeout=300  # 5 минут бездействия
                )
                await self.sequence_process(task['message'], task['task'])
                self.queues[channel_id].task_done()
            except asyncio.CancelledError:
                # Экстренно прерываем процессор при cancel()
                break
            except (asyncio.TimeoutError, KeyError):
                # Удаляем очередь и обработчик при бездействии
                if channel_id in self.queues:
                    del self.queues[channel_id]
                if channel_id in self.processors:
                    del self.processors[channel_id]
                break
            except Exception as e:
                print(f"Ошибка обработки задач: {str(e)}")
    
    async def process_partial_sequence(self, message: discord.Message, task: dict):
        """Добавляет задачи в очередь канала"""
        channel_id = message.channel.id
        
        # Создаем очередь если отсутствует
        if channel_id not in self.queues:
            self.queues[channel_id] = asyncio.Queue()
            
            # Запускаем новый обработчик очереди
            self.processors[channel_id] = asyncio.create_task(
                self.queue_processor(channel_id)
            )

        # Добавляем задачу в очередь
        await self.queues[channel_id].put({
            "message": message,
            "task": task
        })

    async def cancel_pending_sequence(self, channel_id: int):
        """Очищает очередь и останавливает обработчик с восстановлением"""
        if channel_id in self.active_tasks:
            self.active_tasks[channel_id].cancel()
        if channel_id in self.processors:
            self.processors[channel_id].cancel()
        if channel_id in self.active_tasks:
            self.active_tasks[channel_id].cancel()
            
        # Всегда пересоздаем очередь после отмены
        if channel_id in self.queues:
            del self.queues[channel_id]
        if channel_id in self.processors:
            del self.processors[channel_id]
        if channel_id in self.active_tasks:
            del self.active_tasks[channel_id]

        # Принудительно восстанавливаем обработчик
        self.queues[channel_id] = asyncio.Queue()
        self.processors[channel_id] = asyncio.create_task(
            self.queue_processor(channel_id)
        )

    async def on_ready(self):
        print(f"Пользователь {self.bot.user} подключился к Discord!")
        self.alpha.set_channel(ChannelTypes.discord, CHANNEL_ID)
        self.alpha.add_startup_message()

    async def clear(self, ctx):
        """Очищает историю сообщений канала"""
        if not ctx.author.guild_permissions.administrator:
            return await ctx.reply("!Требуются права администратора!")
            
        channel = self.alpha.current_channel
        if channel and channel.id == ctx.channel.id:
            # Очищаем сообщения и заметки связанные с каналом
            if self.alpha.clear_current_channel():
                await ctx.reply(f"!История канала {ctx.channel.name} очищена!")
            else:
                await ctx.reply(f"!Ошибка: неизвестная ошибка")
        else:
            await ctx.reply("!Ошибка: канал не найден в памяти")

    async def clear_notes(self, ctx):
        """Очищает заметки"""
        if not ctx.author.guild_permissions.administrator:
            return await ctx.reply("!Требуются права администратора!")
        
        # Очищаем сообщения и заметки связанные с каналом
        if self.alpha.clear_notes():
            await ctx.reply(f"!История заметок очищена!")
        else:
            await ctx.reply(f"!Ошибка: неизвестная ошибка")
    
    async def on_command(self, message):
        if message.content.startswith("!clear_notes"):
            await self.clear_notes(message)
        elif message.content.startswith("!clear"):
            await self.clear(message)

    async def handle_stream_response(self, message: discord.Message):
        try:
            alpha = self.alpha
            metainfo = {"reply_message_id": message.reference.message_id} if message.reference else {}
            
            msg_obj = Message(
                timestamp=datetime.now().timestamp(),
                text=message.content,
                author=message.author.display_name,
                id=message.id,
                metainfo=metainfo
            )
            
            async for task in alpha.process_message_stream(msg_obj, message):
                print(json.dumps(task, indent=2, ensure_ascii=False))
                await self.process_partial_sequence(message, task)
                
        except Exception as e:
            await message.channel.send(f"Ошибка: {str(e)}")

    async def on_message(self, message: discord.Message):
        # Игнорируем сообщения от ботов и других каналов
        if message.author.bot:
            return
        if message.channel.id != self.alpha.current_channel.id:
            return
        
        # Обработка команд
        if message.content.startswith("!"):
            await self.on_command(message)
            return
        
        try:
            # Отменяем текущую очередь задач для этого канала
            await self.cancel_pending_sequence(message.channel.id)
            
            # Создаем новую задачу обработки сообщения
            task = self.bot.loop.create_task(
                self.handle_stream_response(message)
            )
            
            # Сохраняем ссылку на задачу для управления
            self.active_tasks[message.channel.id] = task
                
        except Exception as e:
            await message.channel.send(f"Ошибка обработки сообщения: {str(e)}")
            raise e
    
    def run(self):
        """Запуск бота"""
        try:
            self.bot.run(self.token)
        except Exception as e:
            self.alpha.add_error_message()
            raise e