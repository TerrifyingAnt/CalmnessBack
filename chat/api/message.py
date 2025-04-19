from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
import json
import logging

from core.database import get_db
from schemas.message import Message, MessageCreate, MessageUpdate
from services.message_service import MessageService
from services.minio_service import minio_service

router = APIRouter()
logger = logging.getLogger(__name__)

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
    
    # Replace file paths with presigned URLs in the media field
    for message in messages:
        if message.media:
            file_paths = message.media.split(",")
            presigned_urls = []
            files_data = []
            
            for file_path in file_paths:
                if file_path.strip():
                    try:
                        file_url = minio_service.get_file_url(file_path)
                        file_name = file_path.split("/")[-1] if "/" in file_path else file_path
                        
                        # Add presigned URL to the list
                        presigned_urls.append(file_url)
                        
                        # Try to determine content type for files info
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
                        
                        files_data.append({
                            "file_path": file_path,
                            "file_url": file_url,
                            "file_name": file_name,
                            "content_type": content_type
                        })
                    except Exception as e:
                        logger.error(f"Error processing file {file_path}: {str(e)}")
                        # Skip files that can't be processed
                        continue
            
            # Replace media with comma-separated presigned URLs
            message.media = ",".join(presigned_urls)
            # Keep files data for backward compatibility
            message.files = files_data
    
    return messages

@router.post("/", response_model=Message)
async def create_message(
    text: str = Form(...),
    chat_id: int = Form(...),
    from_user_id: int = Form(...),
    files: List[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new message with optional file attachments
    """
    # Create the message first
    message_create = MessageCreate(
        from_user_id=from_user_id,
        chat_id=chat_id,
        text=text,
        status=False
    )
    
    message = await MessageService.create_message(db, message_create)
    
    # Handle file uploads if any
    if files and any(file.filename for file in files):
        file_paths = []
        presigned_urls = []
        files_data = []
        
        for file in files:
            if file.filename:
                try:
                    logger.info(f"Uploading file {file.filename}")
                    # Upload file to MinIO
                    object_name = await minio_service.upload_file(
                        file, 
                        chat_id, 
                        message.id
                    )
                    file_paths.append(object_name)
                    
                    # Get file URL and prepare file info
                    file_url = minio_service.get_file_url(object_name)
                    presigned_urls.append(file_url)
                    
                    files_data.append({
                        "file_path": object_name,
                        "file_url": file_url,
                        "file_name": file.filename,
                        "content_type": file.content_type
                    })
                    logger.info(f"File uploaded successfully: {object_name}")
                except Exception as e:
                    logger.error(f"Error uploading file {file.filename}: {str(e)}")
                    # Continue with other files if one fails
                    continue
        
        # Update message with file paths for database storage
        if file_paths:
            message_update = MessageUpdate(media=",".join(file_paths))
            message = await MessageService.update_message(db, message.id, message_update)
            
            # Set presigned URLs in the response media field
            message.media = ",".join(presigned_urls)
            message.files = files_data
    
    return message

@router.get("/{message_id}", response_model=Message)
async def read_message(
    message_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get specific message by ID with file information
    """
    message = await MessageService.get_message(db, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Replace file paths with presigned URLs in the media field
    if message.media:
        file_paths = message.media.split(",")
        presigned_urls = []
        files_data = []
        
        for file_path in file_paths:
            if file_path.strip():
                try:
                    file_url = minio_service.get_file_url(file_path)
                    file_name = file_path.split("/")[-1] if "/" in file_path else file_path
                    
                    # Add presigned URL to the list
                    presigned_urls.append(file_url)
                    
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
                    
                    files_data.append({
                        "file_path": file_path,
                        "file_url": file_url,
                        "file_name": file_name,
                        "content_type": content_type
                    })
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {str(e)}")
                    # Skip files that can't be processed
                    continue
        
        # Replace media with comma-separated presigned URLs
        message.media = ",".join(presigned_urls)
        # Keep files data for backward compatibility
        message.files = files_data
    
    return message

@router.put("/{message_id}", response_model=Message)
async def update_message(
    message_id: int,
    text: str = Form(None),
    status: bool = Form(None),
    files: List[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Update a message with optional new files
    """
    # Get the existing message
    message = await MessageService.get_message(db, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Prepare update data
    update_data = {}
    if text is not None:
        update_data["text"] = text
    if status is not None:
        update_data["status"] = status
    
    # Handle new file uploads if any
    existing_file_paths = message.media.split(",") if message.media else []
    new_file_paths = []
    files_data = []
    presigned_urls = []
    
    # Process existing files
    for file_path in existing_file_paths:
        if file_path.strip():
            try:
                file_url = minio_service.get_file_url(file_path)
                presigned_urls.append(file_url)
                
                file_name = file_path.split("/")[-1] if "/" in file_path else file_path
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
                
                files_data.append({
                    "file_path": file_path,
                    "file_url": file_url,
                    "file_name": file_name,
                    "content_type": content_type
                })
            except Exception as e:
                logger.error(f"Error processing existing file {file_path}: {str(e)}")
                # Skip files that can't be processed
                continue
    
    # Process new files
    if files and any(file.filename for file in files):
        for file in files:
            if file.filename:
                try:
                    # Upload file to MinIO
                    object_name = await minio_service.upload_file(
                        file, 
                        message.chat_id, 
                        message_id
                    )
                    new_file_paths.append(object_name)
                    
                    # Get file URL and prepare file info
                    file_url = minio_service.get_file_url(object_name)
                    presigned_urls.append(file_url)
                    
                    files_data.append({
                        "file_path": object_name,
                        "file_url": file_url,
                        "file_name": file.filename,
                        "content_type": file.content_type
                    })
                except Exception as e:
                    logger.error(f"Error uploading new file {file.filename}: {str(e)}")
                    # Continue with other files if one fails
                    continue
    
    # Combine existing and new file paths
    all_file_paths = existing_file_paths + new_file_paths
    if all_file_paths:
        update_data["media"] = ",".join([p for p in all_file_paths if p.strip()])
    
    # Update the message
    message = await MessageService.update_message(db, message_id, MessageUpdate(**update_data))
    
    # Set presigned URLs in the response
    message.media = ",".join(presigned_urls)
    message.files = files_data
    
    return message

@router.delete("/{message_id}", response_model=bool)
async def delete_message(
    message_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a message and its associated files
    """
    # Get the message to find associated files
    message = await MessageService.get_message(db, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Delete associated files from MinIO
    if message.media:
        file_paths = message.media.split(",")
        for file_path in file_paths:
            if file_path.strip():
                try:
                    minio_service.delete_file(file_path)
                except Exception as e:
                    logger.error(f"Error deleting file {file_path}: {str(e)}")
                    # Continue even if file deletion fails
                    pass
    
    # Delete the message
    success = await MessageService.delete_message(db, message_id)
    if not success:
        raise HTTPException(status_code=404, detail="Message not found")
    
    return True

@router.delete("/{message_id}/files/{file_name}", response_model=Message)
async def delete_message_file(
    message_id: int,
    file_name: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a specific file from a message
    """
    # Get the message
    message = await MessageService.get_message(db, message_id)
    if message is None:
        raise HTTPException(status_code=404, detail="Message not found")
    
    # Find and delete the file
    if message.media:
        file_paths = message.media.split(",")
        updated_paths = []
        target_file_path = None
        
        # Find the file that matches the filename
        for file_path in file_paths:
            if file_path.strip():
                if file_path.endswith(f"/{file_name}") or file_path == file_name:
                    target_file_path = file_path
                else:
                    updated_paths.append(file_path)
        
        if target_file_path:
            # Delete the file from MinIO
            try:
                minio_service.delete_file(target_file_path)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to delete file: {str(e)}")
            
            # Update the message's media field
            message_update = MessageUpdate(media=",".join(updated_paths) if updated_paths else None)
            message = await MessageService.update_message(db, message_id, message_update)
            
            # Add presigned URLs for remaining files
            presigned_urls = []
            files_data = []
            
            if message.media:
                remaining_file_paths = message.media.split(",")
                
                for file_path in remaining_file_paths:
                    if file_path.strip():
                        try:
                            file_url = minio_service.get_file_url(file_path)
                            presigned_urls.append(file_url)
                            
                            remaining_file_name = file_path.split("/")[-1] if "/" in file_path else file_path
                            
                            # Try to determine content type
                            content_type = "application/octet-stream"
                            if "." in remaining_file_name:
                                ext = remaining_file_name.split(".")[-1].lower()
                                if ext in ["jpg", "jpeg", "png", "gif"]:
                                    content_type = f"image/{ext}"
                                elif ext in ["pdf"]:
                                    content_type = "application/pdf"
                                elif ext in ["doc", "docx"]:
                                    content_type = "application/msword"
                                elif ext in ["txt"]:
                                    content_type = "text/plain"
                            
                            files_data.append({
                                "file_path": file_path,
                                "file_url": file_url,
                                "file_name": remaining_file_name,
                                "content_type": content_type
                            })
                        except Exception as e:
                            logger.error(f"Error processing remaining file {file_path}: {str(e)}")
                            # Skip files that can't be processed
                            continue
            
            # Set presigned URLs in the response
            message.media = ",".join(presigned_urls)
            message.files = files_data
        else:
            raise HTTPException(status_code=404, detail="File not found in message")
    else:
        raise HTTPException(status_code=404, detail="Message has no files")
    
    return message