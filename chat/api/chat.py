from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas.chat import Chat, ChatCreate, ChatUpdate
from services.chat_service import ChatService

router = APIRouter()

@router.get("/", response_model=List[Chat])
async def read_chats(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve all chats with pagination
    """
    chats = await ChatService.get_chats(db, skip=skip, limit=limit)
    return chats

@router.post("/", response_model=Chat)
async def create_chat(
    chat_create: ChatCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new chat
    """
    chat = await ChatService.create_chat(db, chat_create)
    return chat

@router.get("/{chat_id}", response_model=Chat)
async def read_chat(
    chat_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific chat by ID
    """
    chat = await ChatService.get_chat(db, chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@router.put("/{chat_id}", response_model=Chat)
async def update_chat(
    chat_id: int,
    chat_update: ChatUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a chat
    """
    chat = await ChatService.update_chat(db, chat_id, chat_update)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat

@router.delete("/{chat_id}", response_model=bool)
async def delete_chat(
    chat_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a chat
    """
    success = await ChatService.delete_chat(db, chat_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found")
    return True

@router.get("/user/{user_id}", response_model=List[Chat])
async def read_user_chats(
    user_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all chats for a specific user
    """
    chats = await ChatService.get_user_chats(db, user_id)
    return chats