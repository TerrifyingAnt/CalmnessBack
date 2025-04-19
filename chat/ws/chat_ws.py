from typing import Dict, List
import json
import asyncio
from fastapi import WebSocket, WebSocketDisconnect, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
import base64
import io

from core.database import AsyncSessionLocal
from ws.connection_manager import connection_manager
from services.message_service import MessageService
from services.chat_service import ChatService
from services.minio_service import minio_service
from schemas.message import MessageCreate, WebSocketMessage, FileInfo

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
                    
                    # Check if there are files attached
                    files_data = []
                    files = ws_message.data.get("files", [])
                    
                    if files:
                        # Process files if any
                        uploaded_files = []
                        for file_data in files:
                            # Extract file information
                            file_content = base64.b64decode(file_data.get("content", ""))
                            file_name = file_data.get("name", "unnamed_file")
                            content_type = file_data.get("content_type", "application/octet-stream")
                            
                            # Create UploadFile object from data
                            file = UploadFile(
                                filename=file_name,
                                file=io.BytesIO(file_content),
                                content_type=content_type
                            )
                            
                            # Upload to MinIO
                            object_name = await minio_service.upload_file(file, chat_id, db_message.id)
                            file_url = minio_service.get_file_url(object_name)
                            
                            # Create file info
                            file_info = FileInfo(
                                file_path=object_name,
                                file_url=file_url,
                                file_name=file_name,
                                content_type=content_type
                            )
                            
                            files_data.append(file_info.dict())
                            uploaded_files.append(object_name)
                        
                        # Update message with file paths if files were uploaded
                        if uploaded_files:
                            await MessageService.update_message(
                                db,
                                db_message.id,
                                {"media": ",".join(uploaded_files)}
                            )
                            db_message.media = ",".join(uploaded_files)
                    
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
                            "media": db_message.media,
                            "files": files_data
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
                    # Process file information if message has media
                    files_data = []
                    if msg.media:
                        file_paths = msg.media.split(",")
                        for file_path in file_paths:
                            if file_path.strip():
                                try:
                                    file_url = minio_service.get_file_url(file_path)
                                    # Extract filename from path
                                    file_name = file_path.split("/")[-1] if "/" in file_path else file_path
                                    
                                    # Try to determine content type or use a default
                                    content_type = "application/octet-stream"
                                    if "." in file_name:
                                        ext = file_name.split(".")[-1].lower()
                                        if ext in ["jpg", "jpeg", "png", "gif"]:
                                            content_type = f"image/{ext}"
                                        elif ext in ["pdf"]:
                                            content_type = "application/pdf"
                                        elif ext in ["doc", "docx"]:
                                            content_type = "application/msword"
                                        elif ext in ["txt"]:
                                            content_type = "text/plain"
                                    
                                    file_info = {
                                        "file_path": file_path,
                                        "file_url": file_url,
                                        "file_name": file_name,
                                        "content_type": content_type
                                    }
                                    files_data.append(file_info)
                                except Exception as e:
                                    # Skip files that can't be processed
                                    continue
                    
                    message_history.append({
                        "id": msg.id,
                        "from_user_id": msg.from_user_id,
                        "text": msg.text,
                        "date": msg.date.isoformat(),
                        "status": msg.status,
                        "media": msg.media,
                        "files": files_data
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
            
            elif ws_message.type == "delete_file":
                # Delete a file from MinIO storage
                file_path = ws_message.data.get("file_path")
                message_id = ws_message.data.get("message_id")
                
                if file_path and message_id:
                    # Check if user has permission to delete this file
                    message = await MessageService.get_message(db, message_id)
                    if not message or message.from_user_id != user_id:
                        await websocket.send_json({
                            "type": "error",
                            "data": {"message": "Permission denied to delete this file"}
                        })
                        continue
                    
                    # Delete file from MinIO
                    deleted = minio_service.delete_file(file_path)
                    
                    # Update message's media field
                    if deleted and message.media:
                        file_paths = message.media.split(",")
                        file_paths = [fp for fp in file_paths if fp.strip() and fp != file_path]
                        new_media = ",".join(file_paths) if file_paths else None
                        
                        await MessageService.update_message(
                            db,
                            message_id,
                            {"media": new_media}
                        )
                        
                        # Notify all users that file was deleted
                        file_deleted_notification = {
                            "type": "file_deleted",
                            "data": {
                                "message_id": message_id,
                                "file_path": file_path,
                                "deleted_by": user_id
                            }
                        }
                        
                        await connection_manager.broadcast(file_deleted_notification, chat_id)
                
            elif ws_message.type == "file_info":
                # Get information about files in a message
                message_id = ws_message.data.get("message_id")
                
                if message_id:
                    message = await MessageService.get_message(db, message_id)
                    if not message:
                        await websocket.send_json({
                            "type": "error",
                            "data": {"message": "Message not found"}
                        })
                        continue
                    
                    files_data = []
                    if message.media:
                        file_paths = message.media.split(",")
                        for file_path in file_paths:
                            if file_path.strip():
                                try:
                                    file_url = minio_service.get_file_url(file_path)
                                    file_name = file_path.split("/")[-1] if "/" in file_path else file_path
                                    
                                    # Try to determine content type
                                    content_type = "application/octet-stream"
                                    if "." in file_name:
                                        ext = file_name.split(".")[-1].lower()
                                        if ext in ["jpg", "jpeg", "png", "gif"]:
                                            content_type = f"image/{ext}"
                                        elif ext in ["pdf"]:
                                            content_type = "application/pdf"
                                        elif ext in ["doc", "docx"]:
                                            content_type = "application/msword"
                                        elif ext in ["txt"]:
                                            content_type = "text/plain"
                                    
                                    file_info = {
                                        "file_path": file_path,
                                        "file_url": file_url,
                                        "file_name": file_name,
                                        "content_type": content_type
                                    }
                                    files_data.append(file_info)
                                except Exception as e:
                                    # Skip files that can't be processed
                                    continue
                    
                    file_info_data = {
                        "type": "file_info",
                        "data": {
                            "message_id": message_id,
                            "files": files_data
                        }
                    }
                    
                    await websocket.send_json(file_info_data)
                
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