from typing import List, Optional
import time
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete

from models.chat import Chat
from models.user_in_chat import UserInChat
from schemas.chat import ChatCreate, ChatUpdate

class ChatService:
    @staticmethod
    async def get_chat(db: AsyncSession, chat_id: int) -> Optional[Chat]:
        result = await db.execute(select(Chat).filter(Chat.id == chat_id))
        return result.scalars().first()
    
    @staticmethod
    async def get_chats(db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Chat]:
        result = await db.execute(select(Chat).offset(skip).limit(limit))
        return result.scalars().all()
    
    @staticmethod
    async def create_chat(db: AsyncSession, chat_create: ChatCreate) -> Chat:
        current_timestamp = int(time.time())
        
        chat = Chat(
            name=chat_create.name,
            last_message_id=0,  # Initial value
            creation_date=current_timestamp,
            message_status=chat_create.message_status
        )
        
        db.add(chat)
        await db.commit()
        await db.refresh(chat)
        return chat
    
    @staticmethod
    async def update_chat(
        db: AsyncSession, chat_id: int, chat_update: ChatUpdate
    ) -> Optional[Chat]:
        chat = await ChatService.get_chat(db, chat_id)
        if not chat:
            return None
        
        update_data = chat_update.dict(exclude_unset=True)
        
        await db.execute(
            update(Chat)
            .where(Chat.id == chat_id)
            .values(**update_data)
        )
        await db.commit()
        
        return await ChatService.get_chat(db, chat_id)
    
    @staticmethod
    async def delete_chat(db: AsyncSession, chat_id: int) -> bool:
        chat = await ChatService.get_chat(db, chat_id)
        if not chat:
            return False
        
        await db.execute(delete(Chat).where(Chat.id == chat_id))
        await db.commit()
        return True
    
    @staticmethod
    async def get_user_chats(db: AsyncSession, user_id: int) -> List[Chat]:
        result = await db.execute(
            select(Chat)
            .join(UserInChat, UserInChat.chat_id == Chat.id)
            .filter(UserInChat.user_id == user_id)
        )
        return result.scalars().all()