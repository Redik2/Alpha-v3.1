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


CHANNEL_ID = 1124005435507212318


class DiscordBot:
    def __init__(self, alpha: Alpha):
        self.token = discord_token
        self.alpha = alpha
        self.bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
        self.active_tasks: Dict[int, asyncio.Task] = {}  # ID канала: активная задача
        
        # Регистрация обработчиков событий
        self.bot.add_listener(self.on_ready)
        self.bot.add_listener(self.on_message)

    async def send_delayed_messages(self, channel: discord.TextChannel, message_sequence: list):
        """Отправляет сообщения с задержками с возможностью прерывания"""
        try:
            for i in range(len(message_sequence)):
                if message_sequence[i] is None:
                    return
                typing_time = len(message_sequence[i]["content"]) * 0.05 * (0.75 + random.random() * 0.5)
                waiting_tyme = max(message_sequence[i + 1]["delay_sec"] * (0.75 + random.random() * 0.5) - typing_time, 0)

                async with channel.typing():
                    await asyncio.sleep(typing_time)
                await channel.send(message_sequence[i]["content"])
                if i + 1 < len(message_sequence):
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
        print(f"Бот {self.bot.user} подключился к Discord!")
        self.alpha.set_channel(ChannelTypes.discord, CHANNEL_ID)

    async def on_message(self, message: discord.Message):
        if message.channel.id != self.alpha.current_channel.id:
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
        
        self.alpha.set_channel(ChannelTypes.discord, message.channel.id)
        
        try:
            response = self.alpha.process_message(
                text=message.content,
                author=str(message.author)
            )
            
            message_sequence = response.get("message_sequence", [])
            
            if message_sequence:
                # Создаем новую задачу и сохраняем ее
                task = self.bot.loop.create_task(
                    self.send_delayed_messages(message.channel, message_sequence)
                )
                self.active_tasks[message.channel.id] = task
                
        except Exception as e:
            await message.channel.send(f"Ошибка: {str(e)}")
            print(f"Discord Error: {str(e)}")

    def run(self):
        """Запуск бота"""
        self.bot.run(self.token)