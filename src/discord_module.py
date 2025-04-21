import discord
import asyncio
import json
from datetime import datetime
from typing import Optional, Dict
from discord.ext import commands
from src.alpha import Alpha
from src.memory import ChannelTypes, Message
from keys import discord_token
import random


CHANNEL_ID = 1074390741238956163


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

    async def send_delayed_messages(self, channel: discord.TextChannel, message_sequence: list):
        """Отправляет сообщения с задержками с возможностью прерывания"""
        try:
            for i in range(len(message_sequence)):
                if message_sequence[i] is None:
                    waiting_tyme = max(message_sequence[i + 1]["delay_sec"] * (0.75 + random.random() * 0.5), 0)
                    if i + 1 < len(message_sequence):
                        await asyncio.sleep(waiting_tyme)
                    continue
                typing_time = len(message_sequence[i]["content"]) * 0.05 * (0.75 + random.random() * 0.5)

                async with channel.typing():
                    await asyncio.sleep(typing_time)
                if message_sequence[i]:
                    await channel.send(message_sequence[i]["content"])
                if i + 1 < len(message_sequence):
                    waiting_tyme = max(message_sequence[i + 1]["delay_sec"] * (0.75 + random.random() * 0.5) - typing_time, 0)
                    await asyncio.sleep(waiting_tyme)
        except asyncio.CancelledError:
            return
        finally:
            # Гарантированно удаляем задачу из словаря
            if channel.id in self.active_tasks:
                del self.active_tasks[channel.id]


    async def cancel_pending_messages(self, channel_id: int):
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
        if message.channel.id != self.alpha.current_channel.id:
            return
        if message.content.startswith("!"):
            await self.on_command(message)
            return
        if message.author.bot:
            self.alpha.memory.add_message(self.alpha.current_channel,
                                          Message(
                timestamp=datetime.now().timestamp(),
                text=message.content,
                author="Alpha"
            ))
            return

        # Прерываем текущую цепочку сообщений в этом канале
        await self.cancel_pending_messages(message.channel.id)
        
        try:
            response = self.alpha.process_message(
                text=message.content,
                author=str(message.author.display_name)
            )
            print("==========================================================================")
            print(response)
            message_sequence: list = response.get("message_sequence", [])
            dialog_iniciation = response.get("dialog_iniciation", None)
            if dialog_iniciation:
                message_sequence.append({"delay_sec": dialog_iniciation["time"], "content": dialog_iniciation["content"]})
            
            if message_sequence:
                # Создаем новую задачу и сохраняем ее
                task = self.bot.loop.create_task(
                    self.send_delayed_messages(message.channel, message_sequence)
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