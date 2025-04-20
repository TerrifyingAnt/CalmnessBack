from typing import List, Optional
from datetime import datetime
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete

from models.message import Message
from models.chat import Chat
from models.user import User
from schemas.message import MessageCreate, MessageUpdate
from services.emotion_service import emotion_service

logger = logging.getLogger(__name__)

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
        
        # Для любого типа пользователя делаем анализ эмоций текста
        try:
            logger.info(f"Анализ эмоций для сообщения от пользователя (ID: {message_create.from_user_id})")
            
            emotional_state = emotion_service.analyze_sentiment(message_create.text)
            message.emotional_state = emotional_state
            
            emotion = emotion_service.classify_emotion(message_create.text)
            message.emotion = emotion
            
            logger.info(f"Результат анализа текста: состояние = {emotional_state}, эмоция = {emotion}")
        except Exception as e:
            logger.error(f"Ошибка при анализе эмоций текста: {str(e)}")
        
        db.add(message)
        await db.commit()
        await db.refresh(message)
        
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
        
        if 'text' in update_data:
            try:
                user_result = await db.execute(
                    select(User).filter(User.id == message.from_user_id)
                )
                user = user_result.scalars().first()
                
                if user and user.type_id == 2:
                    logger.info(f"Пересчет эмоций при обновлении сообщения от пациента (ID: {user.id})")
                    
                    update_data['emotional_state'] = emotion_service.analyze_sentiment(update_data['text'])
                    
                    update_data['emotion'] = emotion_service.classify_emotion(update_data['text'])
                    
                    logger.info(f"Результат анализа: состояние = {update_data['emotional_state']}, эмоция = {update_data['emotion']}")
            except Exception as e:
                logger.error(f"Ошибка при анализе эмоций при обновлении: {str(e)}")
        
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