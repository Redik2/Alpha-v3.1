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

class Note:
    def __init__(self, timestamp: float, text: str, id: int, type: str):
        self.timestamp = timestamp
        self.text = text
        self.id = id
        self.type = type
        
    def to_dict(self) -> dict:
        return {
            'timestamp': self.timestamp,
            'text': self.text,
            'id': self.id,
            'type': self.type
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Message':
        return cls(
            timestamp=data['timestamp'],
            text=data['text'],
            id=data['id'],
            type=data['type']
        )


class Memory:
    def __init__(self, file_path: str = 'memory.json'):
        self.file_path = file_path
        self.data: Dict[str, Dict[Channel, List[Message]] | List[Note]] = {}
        self.notes_edit_counter = 0
        self.load()
    
    def add_channel(self, channel: Channel) -> None:
        if channel not in self.data["channels"]:
            self.data["channels"][channel] = []
            
    def add_message(self, channel: Channel, message: Message) -> None:
        if channel not in self.data["channels"]:
            self.add_channel(channel)
        self.data["channels"][channel].append(message)
            
    def add_note(self, note: Note) -> None:
        for note_ in self.data["notes"]:
            if note_.id == note.id:
                self.data["notes"][self.data["notes"].index(note_)] = note
                return
        self.data["notes"].append(note)

        self.notes_edit_counter += 1
        if self.notes_edit_counter > 10:
            self.notes_edit_counter = 0
            self.create_backup_notes()
            
    def remove_note(self, id: int) -> None:
        for note in self.data["notes"]:
            if note.id == id:
                self.data["notes"].remove(note)
                return

        self.notes_edit_counter += 1
        if self.notes_edit_counter > 10:
            self.notes_edit_counter = 0
            self.create_backup_notes()
    
    def get_notes(self) -> List[Note]:
        return self.data["notes"]
        
    def get_messages(self, channel: Channel) -> List[Message]:
        all_messages = self.data["channels"].get(channel, [])
        return all_messages[-10:] if len(all_messages) >= 10 else all_messages[:]
    
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
        "notes": [note.to_dict() for note in self.data["notes"]]
        }
        with open(self.file_path, 'w', encoding="utf-8") as f:
            json.dump(serialized, f, indent=4, ensure_ascii=False)
        
    
    def create_backup_notes(self) -> None:
        serialized = {
        "notes": [note.to_dict() for note in self.data["notes"]]
        }
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"notes_backup_{timestamp}.json"
        with open(f"notes_backups/{backup_name}", 'x', encoding="utf-8") as f:
            json.dump(serialized, f, indent=4, ensure_ascii=False)
    
            
    def load(self) -> None:
        try:
            with open(self.file_path, 'r', encoding="utf-8") as f:
                data = json.load(f)
                
            self.data = {"channels": {}, "notes": []}
            for key, messages in data["channels"].items():
                channel_type, channel_id = map(int, key.split(':'))
                channel = Channel(channel_type, channel_id)
                self.data["channels"][channel] = [Message.from_dict(msg) for msg in messages]
            
            self.data["notes"] = [Note.from_dict(note) for note in data["notes"]]
                
        except FileNotFoundError:
            self.data = {"channels": {}, "notes": []}
        except KeyError:
            self.data = {"channels": {}, "notes": []}