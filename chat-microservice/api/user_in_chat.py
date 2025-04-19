from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import delete

from core.database import get_db
from models.user_in_chat import UserInChat
from schemas.user_in_chat import UserInChat as UserInChatSchema
from schemas.user_in_chat import UserInChatCreate

router = APIRouter()

@router.post("/", response_model=UserInChatSchema)
async def add_user_to_chat(
    user_in_chat: UserInChatCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Add a user to a chat
    """
    # Check if the user is already in the chat
    result = await db.execute(
        select(UserInChat).filter(
            UserInChat.chat_id == user_in_chat.chat_id,
            UserInChat.user_id == user_in_chat.user_id
        )
    )
    existing = result.scalars().first()
    
    if existing:
        raise HTTPException(
            status_code=400, 
            detail="User is already in this chat"
        )
    
    # Create new membership
    db_user_in_chat = UserInChat(**user_in_chat.dict())
    db.add(db_user_in_chat)
    await db.commit()
    await db.refresh(db_user_in_chat)
    
    return db_user_in_chat

@router.get("/chat/{chat_id}", response_model=List[UserInChatSchema])
async def get_users_in_chat(
    chat_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all users in a specific chat
    """
    result = await db.execute(
        select(UserInChat).filter(UserInChat.chat_id == chat_id)
    )
    return result.scalars().all()

@router.get("/user/{user_id}", response_model=List[UserInChatSchema])
async def get_chats_for_user(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all chats for a specific user
    """
    result = await db.execute(
        select(UserInChat).filter(UserInChat.user_id == user_id)
    )
    return result.scalars().all()

@router.delete("/{chat_id}/{user_id}", response_model=bool)
async def remove_user_from_chat(
    chat_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Remove a user from a chat
    """
    result = await db.execute(
        delete(UserInChat).filter(
            UserInChat.chat_id == chat_id,
            UserInChat.user_id == user_id
        )
    )
    
    await db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail="User not found in this chat"
        )
    
    return True