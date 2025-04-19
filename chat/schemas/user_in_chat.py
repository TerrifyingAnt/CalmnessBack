from pydantic import BaseModel

class UserInChatBase(BaseModel):
    chat_id: int
    user_id: int

class UserInChatCreate(UserInChatBase):
    pass

class UserInChatUpdate(UserInChatBase):
    pass

class UserInChatInDB(UserInChatBase):
    id: int
    
    class Config:
        orm_mode = True

class UserInChat(UserInChatInDB):
    pass