from datetime import datetime
import json
from typing import Dict, List, Optional, LiteralString


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
    
    def __str__(self):
        return f"{self.type}:{self.id}"


class Message:
    def __init__(self, timestamp: float, text: str, author: str, id: int = -1):
        self.timestamp = timestamp
        self.text = text
        self.author = author
        self.id = id
        
    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp,
            'text': self.text,
            'author': self.author,
            'id': self.id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Message':
        return cls(
            timestamp=data['timestamp'],
            text=data['text'],
            author=data['author'],
            id=data['id'] if "id" in data.keys() else -1
        )

class MemoryCell:
    def __init__(self, timestamp: float, text: str, id: int):
        self.timestamp = timestamp
        self.text = text
        self.id = id
        
    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp,
            'text': self.text,
            'id': self.id
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Message':
        return cls(
            timestamp=data['timestamp'],
            text=data['text'],
            id=data['id']
        )


class Memory:
    def __init__(self, file_path: str = 'memory.json'):
        self.file_path = file_path
        self.data: Dict[str, Dict[Channel, List[Message]] | Dict[str, List[MemoryCell]]] = {}
        self.memories_edit_counter = 0
        self.load()
    
    def add_channel(self, channel: Channel) -> None:
        if channel not in self.data["channels"]:
            self.data["channels"][channel] = []
            
    def add_message(self, channel: Channel, message: Message) -> None:
        if channel not in self.data["channels"]:
            self.add_channel(channel)
        self.data["channels"][channel].append(message)
            
    def add_memory(self, topic: str, memory: MemoryCell) -> None:
        if topic not in self.data["memory"].keys():
            self.data["memory"][topic] = []
        self.data["memory"][topic].append(memory)
        self.backup_counter()
    
    def edit_memory(self, topic: str, memory: MemoryCell) -> None:
        for memory_ in self.data["memory"][topic]:
            if memory_.id == memory.id:
                self.data["memory"][topic][self.data["memory"][topic].index(memory_)] = memory
                self.backup_counter()
                return
            
    def remove_memory(self, topic: str, id: int) -> None:
        for memory_ in self.data["memory"][topic]:
            if memory_.id == id:
                self.data["memory"][topic].remove(memory_)
                self.backup_counter()
                return
    
    def get_memory(self) -> Dict[str, List[MemoryCell]]:
        return self.data["memory"]
        
    def get_messages(self, channel: Channel) -> List[Message]:
        all_messages = self.data["channels"].get(channel, [])
        return all_messages[-10:] if len(all_messages) >= 10 else all_messages[:]
    
    def find_message(self, channel: Channel, id: int) -> Message | None:
        all_messages = self.data["channels"].get(channel, [])
        for msg in all_messages:
            if msg.id == id:
                return msg
        return None
    
    def find_channel(self, channel_type: int, channel_id: int) -> Optional[Channel]:
        for ch in self.data["channels"].keys():
            if ch.type == channel_type and ch.id == channel_id:
                return ch
        return None
    
    def clear_channel(self, channel: Channel) -> None:
        channel = self.find_channel(channel.type, channel.id)
        if not channel:
            return
        self.data["channels"][channel].clear()
    
    def save(self) -> None:
        serialized = {"channels": {
            str(channel): [msg.to_dict() for msg in messages]
            for channel, messages in self.data["channels"].items()
        },
        "memory": {}
        }
        for topic in self.data["memory"].keys():
            serialized["memory"][topic] = [cell.to_dict() for cell in self.data["memory"][topic]]
        with open(self.file_path, 'w', encoding="utf-8") as f:
            json.dump(serialized, f, indent=4, ensure_ascii=False)
        
    
    def create_backup_memories(self) -> None:
        serialized = {
        "memory": {}
        }
        for topic in self.data["memory"].keys():
            serialized["memory"][topic] = [cell.to_dict() for cell in self.data["memory"][topic]]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"memory_backup_{timestamp}.json"
        with open(f"backups/{backup_name}", 'x', encoding="utf-8") as f:
            json.dump(serialized, f, indent=4, ensure_ascii=False)
    
    def backup_counter(self) -> None:
        self.memories_edit_counter += 1
        if self.memories_edit_counter > 3:
            self.memories_edit_counter = 0
            self.create_backup_memories()
            
    def load(self) -> None:
        try:
            with open(self.file_path, 'r', encoding="utf-8") as f:
                data = json.load(f)
                
            self.data = {"channels": {}, "memory": {}}
            for key, messages in data["channels"].items():
                channel_type, channel_id = map(int, key.split(':'))
                channel = Channel(channel_type, channel_id)
                self.data["channels"][channel] = [Message.from_dict(msg) for msg in messages]
            
            for topic in data["memory"].keys():
                self.data["memory"][topic] = [MemoryCell.from_dict(cell) for cell in data["memory"][topic]]
                
        except FileNotFoundError:
            self.data = {"channels": {}, "memory": {}}
        except KeyError:
            self.data = {"channels": {}, "memory": {}}