
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

class ChatBase(BaseModel):
    name: int
    message_status: int

class ChatCreate(ChatBase):
    pass

class ChatUpdate(ChatBase):
    name: Optional[int] = None
    last_message_id: Optional[int] = None
    message_status: Optional[int] = None

class ChatInDB(ChatBase):
    id: int
    last_message_id: int
    creation_date: int
    
    class Config:
        orm_mode = True

class Chat(ChatInDB):
    pass