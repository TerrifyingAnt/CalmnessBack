from typing import List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete

from models.message import Message
from models.chat import Chat
from schemas.message import MessageCreate, MessageUpdate

class MessageService:
    @staticmethod
    async def get_message(db: AsyncSession, message_id: int) -> Optional[Message]:
        result = await db.execute(select(Message).filter(Message.id == message_id))
        return result.scalars().first()
    
    @staticmethod
    async def get_chat_messages(
        db: AsyncSession, chat_id: int, skip: int = 0, limit: int = 100
    ) -> List[Message]:
        result = await db.execute(
            select(Message)
            .filter(Message.chat_id == chat_id)
            .order_by(Message.date.desc())
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def create_message(db: AsyncSession, message_create: MessageCreate) -> Message:
        message = Message(
            from_user_id=message_create.from_user_id,
            chat_id=message_create.chat_id,
            text=message_create.text,
            status=message_create.status,
            date=datetime.utcnow(),
            media=None
        )
        
        db.add(message)
        await db.commit()
        await db.refresh(message)
        
        # Update last message ID in chat
        await db.execute(
            update(Chat)
            .where(Chat.id == message_create.chat_id)
            .values(last_message_id=message.id)
        )
        await db.commit()
        
        return message
    
    @staticmethod
    async def update_message(
        db: AsyncSession, message_id: int, message_update: MessageUpdate
    ) -> Optional[Message]:
        message = await MessageService.get_message(db, message_id)
        if not message:
            return None
        
        update_data = message_update.dict(exclude_unset=True)
        
        await db.execute(
            update(Message)
            .where(Message.id == message_id)
            .values(**update_data)
        )
        await db.commit()
        
        return await MessageService.get_message(db, message_id)
    
    @staticmethod
    async def delete_message(db: AsyncSession, message_id: int) -> bool:
        message = await MessageService.get_message(db, message_id)
        if not message:
            return False
        
        await db.execute(delete(Message).where(Message.id == message_id))
        await db.commit()
        return True