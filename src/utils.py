import datetime
import re
import discord

def replace_mentions_with_nicks(text: str, message: discord.Message) -> str:
    """
    Заменяет <@ID> на @display_name
    """
    def replace_match(match):
        user_id = int(match.group(1))
        member = message.guild.get_member(user_id)
        return f'@{member.display_name}' if member else match.group(0)
    
    return re.sub(r'<@!?(\d+)>', replace_match, text)

def replace_nicks_with_mentions(text: str, message: discord.Message) -> str:
    """
    Заменяет @display_name на <@ID>, учитывая пробелы и спецсимволы
    """
    guild = message.guild
    if not guild:
        return text

    # Создаем словарь display_name.lower() -> Member
    display_names = {
        m.display_name.lower(): m
        for m in guild.members
    }

    # Регулярка для захвата всего содержимого до границы слова
    pattern = r'@((?:[^\s<]| )+?)(?=\W|$)'

    def replace_match(match):
        raw_name = match.group(1).rstrip('.,!?;:')  # Удаляем пунктуацию в конце
        member = display_names.get(raw_name.lower())
        return f'<@{member.id}>' if member else f'@{raw_name}'

    return re.sub(pattern, replace_match, text, flags=re.IGNORECASE)

def generate_id() -> int:
    return int(round(float(str(datetime.datetime.now().timestamp() * 23456)))) + 123456789