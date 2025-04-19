from datetime import datetime
import json
from typing import Dict, List, Optional


class ChannelTypes:
    console = 0
    voice = 1
    discord = 2
    telegram = 3


class Channel:
    def __init__(self, channel_type: int, channel_id: int):
        self.type = channel_type
        self.id = channel_id
        
    def to_dict(self) -> dict:
        return {
            'type': self.type,
            'id': self.id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Channel':
        return cls(
            channel_type=data['type'],
            channel_id=data['id']
        )


class Message:
    def __init__(self, timestamp: float, text: str, author: str):
        self.timestamp = timestamp
        self.text = text
        self.author = author
        
    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp,
            'text': self.text,
            'author': self.author
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Message':
        return cls(
            timestamp=data['timestamp'],
            text=data['text'],
            author=data['author']
        )


class Memory:
    def __init__(self, file_path: str = 'memory.json'):
        self.file_path = file_path
        self.data: Dict[Channel, List[Message]] = {}
        self.load()
        
    def _channel_key(self, channel: Channel) -> str:
        return f"{channel.type}:{channel.id}"
    
    def add_channel(self, channel: Channel) -> None:
        if channel not in self.data:
            self.data[channel] = []
            
    def add_message(self, channel: Channel, message: Message) -> None:
        if channel not in self.data:
            self.add_channel(channel)
        self.data[channel].append(message)
        
    def get_messages(self, channel: Channel) -> List[Message]:
        return self.data.get(channel, [])
    
    def find_channel(self, channel_type: int, channel_id: int) -> Optional[Channel]:
        for ch in self.data.keys():
            if ch.type == channel_type and ch.id == channel_id:
                return ch
        return None
    
    def save(self) -> None:
        serialized = {
            self._channel_key(channel): [msg.to_dict() for msg in messages]
            for channel, messages in self.data.items()
        }
        with open(self.file_path, 'w', encoding="utf-8") as f:
            json.dump(serialized, f, indent=4, ensure_ascii=False)
            
    def load(self) -> None:
        try:
            with open(self.file_path, 'r', encoding="utf-8") as f:
                data = json.load(f)
                
            self.data = {}
            for key, messages in data.items():
                channel_type, channel_id = map(int, key.split(':'))
                channel = Channel(channel_type, channel_id)
                self.data[channel] = [Message.from_dict(msg) for msg in messages]
                
        except FileNotFoundError:
            self.data = {}