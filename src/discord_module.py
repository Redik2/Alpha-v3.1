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
        self.active_tasks: Dict[int, asyncio.Task] = {}  # ID канала: активная задача
        
        self.alpha.set_channel(ChannelTypes.discord, CHANNEL_ID)

        # Регистрация обработчиков событий
        self.bot.add_listener(self.on_ready)
        self.bot.add_listener(self.on_message)

    async def sequence_process(self, message: discord.Message, sequence: list):
        """Отправляет сообщения с задержками с возможностью прерывания"""
        channel = message.channel
        try:
            for task in sequence:
                match task["action_name"]:
                    case "send_message":
                        typing_time = len(task["content"]) * 0.04 * (0.75 + random.random() * 0.5)
                        async with channel.typing():
                            await asyncio.sleep(typing_time)
                            content = utils.replace_nicks_with_mentions(task["content"], message)

                            if not "reply_message_id" in task.keys():
                                new_msg = await channel.send(content)
                            else:
                                msg = await channel.fetch_message(task["reply_message_id"])
                                new_msg = await msg.reply(content)
                            
                            self.alpha.memory.add_message(self.alpha.current_channel,
                                                        Message(
                                timestamp=datetime.now().timestamp(),
                                text=content,
                                author="Alpha",
                                id=new_msg.id
                            ))
                    case "edit_message":
                        msg = await channel.fetch_message(task["message_id"])
                        new_content = task["new_content"]
                        await msg.edit(content=new_content)
                        self.alpha.memory.find_message(self.alpha.current_channel, task["message_id"]).text = new_content + " (изменено)"

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
                            continue
                        await msg.add_reaction(task['emoji'])
                self.alpha.memory.save()
        except asyncio.CancelledError:
            return
        finally:
            # Гарантированно удаляем задачу из словаря
            if channel.id in self.active_tasks:
                del self.active_tasks[channel.id]


    async def cancel_pending_sequence(self, channel_id: int):
        """Отменяет текущую задачу отправки сообщений для канала"""
        if channel_id in self.active_tasks:
            task = self.active_tasks[channel_id]
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
            # Удаление происходит в finally блока send_delayed_messages

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

    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if message.channel.id != self.alpha.current_channel.id:
            return
        if message.content.startswith("!"):
            await self.on_command(message)
            return

        # Прерываем текущую цепочку сообщений в этом канале
        await self.cancel_pending_sequence(message.channel.id)
        
        try:
            response = self.alpha.process_message(
                Message(timestamp=datetime.now().timestamp(),
                        text=message.content,
                        author=message.author.display_name,
                        id=message.id), message
            )
            print("==========================================================================")
            print(response)
            sequence: list = response.get("action_sequence", [])
            
            if sequence:
                # Создаем новую задачу и сохраняем ее
                task = self.bot.loop.create_task(
                    self.sequence_process(message, sequence)
                )
                self.active_tasks[message.channel.id] = task
                
        except Exception as e:
            await message.channel.send(f"Ошибка: {str(e)}")
            print(f"Discord Error: {str(e)}")
            raise e
    
    def run(self):
        """Запуск бота"""
        try:
            self.bot.run(self.token)
        except Exception as e:
            self.alpha.add_error_message()
            raise e