from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from schemas.message import Message, MessageCreate, MessageUpdate
from services.message_service import MessageService

router = APIRouter()

@router.get("/chat/{chat_id}", response_model=List[Message])
async def read_chat_messages(
    chat_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve all messages for a specific chat with pagination
    """
    messages = await MessageService.get_chat_messages(db, chat_id, skip=skip, limit=limit)
    return messages

@router.post("/", response_model=Message)
async def create_message(
    message_create: MessageCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new message
    """
    message = await MessageService.create_message(db, message_create)
    return message

@router.get("/{message_id}", response_model=Message)
async def read_message(
    message_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific message by ID
    """
    message = await MessageService.get_message(db, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return message

@router.put("/{message_id}", response_model=Message)
async def update_message(
    message_id: int,
    message_update: MessageUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a message
    """
    message = await MessageService.update_message(db, message_id, message_update)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    return message

@router.delete("/{message_id}", response_model=bool)
async def delete_message(
    message_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a message
    """
    success = await MessageService.delete_message(db, message_id)
    if not success:
        raise HTTPException(status_code=404, detail="Message not found")
    return True