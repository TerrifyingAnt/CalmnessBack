from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel

class MessageBase(BaseModel):
    from_user_id: int
    chat_id: int
    text: str
    status: bool = False

class MessageCreate(MessageBase):
    pass

class MessageUpdate(BaseModel):
    text: Optional[str] = None
    media: Optional[str] = None
    status: Optional[bool] = None

class FileInfo(BaseModel):
    file_path: str
    file_url: str
    file_name: str
    content_type: str

class MessageInDB(MessageBase):
    id: int
    date: datetime
    media: Optional[str] = None
    
    class Config:
        orm_mode = True

class Message(MessageInDB):
    files: Optional[List[FileInfo]] = None

class WebSocketMessage(BaseModel):
    type: str  # 'message', 'join', 'leave', etc.
    data: dict