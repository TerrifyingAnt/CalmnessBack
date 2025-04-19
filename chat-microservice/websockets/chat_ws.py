from typing import Dict
import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import AsyncSessionLocal
from app.websockets.connection_manager import connection_manager
from app.services.message_service import MessageService
from app.services.chat_service import ChatService
from app.schemas.message import MessageCreate, WebSocketMessage

async def get_db_for_ws():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def chat_endpoint(
    websocket: WebSocket,
    chat_id: int,
    user_id: int,
    db: AsyncSession = Depends(get_db_for_ws)
):
    # Verify chat exists and user is a member
    chat = await ChatService.get_chat(db, chat_id)
    if not chat:
        await websocket.close(code=4004, reason="Chat not found")
        return
    
    # Check if user is in the chat (could be more optimized)
    user_chats = await ChatService.get_user_chats(db, user_id)
    if not any(c.id == chat_id for c in user_chats):
        await websocket.close(code=4003, reason="User not in this chat")
        return
    
    # Connect to the chat
    await connection_manager.connect(websocket, chat_id, user_id)
    
    # Notify others that user joined
    join_message = {
        "type": "user_joined",
        "data": {
            "user_id": user_id,
            "chat_id": chat_id,
            "timestamp": asyncio.get_event_loop().time()
        }
    }
    await connection_manager.broadcast(join_message, chat_id, exclude_user_id=user_id)
    
    try:
        while True:
            # Receive message from WebSocket
            data = await websocket.receive_text()
            message_data = json.loads(data)
            
            # Parse the WebSocket message
            try:
                ws_message = WebSocketMessage.parse_obj(message_data)
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "data": {"message": "Invalid message format"}
                })
                continue
            
            # Handle different message types
            if ws_message.type == "message":
                # Create and save message to database
                message_create = MessageCreate(
                    from_user_id=user_id,
                    chat_id=chat_id,
                    text=ws_message.data.get("text", ""),
                    status=False
                )
                
                try:
                    db_message = await MessageService.create_message(db, message_create)
                    
                    # Broadcast message to all users in the chat
                    broadcast_data = {
                        "type": "new_message",
                        "data": {
                            "id": db_message.id,
                            "from_user_id": db_message.from_user_id,
                            "chat_id": db_message.chat_id,
                            "text": db_message.text,
                            "date": db_message.date.isoformat(),
                            "status": db_message.status,
                            "media": db_message.media
                        }
                    }
                    
                    await connection_manager.broadcast(broadcast_data, chat_id)
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "data": {"message": f"Failed to save message: {str(e)}"}
                    })
            
            elif ws_message.type == "typing":
                # Broadcast typing status to other users
                typing_data = {
                    "type": "user_typing",
                    "data": {
                        "user_id": user_id,
                        "chat_id": chat_id,
                        "is_typing": ws_message.data.get("is_typing", True)
                    }
                }
                
                await connection_manager.broadcast(typing_data, chat_id, exclude_user_id=user_id)
            
            elif ws_message.type == "read":
                # Update message status as read
                message_id = ws_message.data.get("message_id")
                if message_id:
                    await MessageService.update_message(
                        db, 
                        message_id, 
                        {"status": True}
                    )
                    
                    # Notify sender that message was read
                    read_notification = {
                        "type": "message_read",
                        "data": {
                            "message_id": message_id,
                            "read_by": user_id
                        }
                    }
                    
                    await connection_manager.broadcast(read_notification, chat_id)
            
            elif ws_message.type == "fetch_history":
                # Get chat history (most recent messages)
                limit = ws_message.data.get("limit", 50)
                skip = ws_message.data.get("skip", 0)
                
                messages = await MessageService.get_chat_messages(db, chat_id, skip=skip, limit=limit)
                
                # Format and send chat history
                message_history = []
                for msg in messages:
                    message_history.append({
                        "id": msg.id,
                        "from_user_id": msg.from_user_id,
                        "text": msg.text,
                        "date": msg.date.isoformat(),
                        "status": msg.status,
                        "media": msg.media
                    })
                
                history_data = {
                    "type": "chat_history",
                    "data": {
                        "chat_id": chat_id,
                        "messages": message_history,
                        "total": len(message_history)
                    }
                }
                
                await websocket.send_json(history_data)
            
            elif ws_message.type == "fetch_active_users":
                # Get active users in the chat
                active_users = connection_manager.get_active_users_in_chat(chat_id)
                
                active_users_data = {
                    "type": "active_users",
                    "data": {
                        "chat_id": chat_id,
                        "users": active_users
                    }
                }
                
                await websocket.send_json(active_users_data)
                
    except WebSocketDisconnect:
        # Handle disconnection
        connection_manager.disconnect(chat_id, user_id)
        
        # Notify others that user left
        leave_message = {
            "type": "user_left",
            "data": {
                "user_id": user_id,
                "chat_id": chat_id,
                "timestamp": asyncio.get_event_loop().time()
            }
        }
        
        await connection_manager.broadcast(leave_message, chat_id)
    
    except Exception as e:
        # Handle any other exceptions
        connection_manager.disconnect(chat_id, user_id)
        print(f"Error in chat WebSocket: {str(e)}")