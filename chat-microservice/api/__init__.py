from fastapi import APIRouter
from api import chat, message, user_in_chat

api_router = APIRouter()

api_router.include_router(chat.router, prefix="/chats", tags=["chats"])
api_router.include_router(message.router, prefix="/messages", tags=["messages"])
api_router.include_router(user_in_chat.router, prefix="/user-in-chat", tags=["user-in-chat"])