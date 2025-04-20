from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
import json
import logging
import os

from core.database import get_db
from schemas.message import Message, MessageCreate, MessageUpdate
from services.message_service import MessageService
from services.minio_service import minio_service
from services.emotion_service import emotion_service

router = APIRouter()
logger = logging.getLogger(__name__)

# List of allowed audio file extensions
ALLOWED_AUDIO_EXTENSIONS = ['.mp3', '.wav', '.ogg', '.m4a']

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
                        
                        # Try to determine content type
                        content_type = "application/octet-stream"
                        if "." in file_name:
                            ext = file_name.split(".")[-1].lower()
                            if ext in ["mp3", "wav", "ogg", "m4a"]:
                                content_type = f"audio/{ext}"
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

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
import io
import logging

from core.database import get_db
from schemas.message import Message, MessageCreate, MessageUpdate
from services.message_service import MessageService
from services.minio_service import minio_service

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/", response_model=Message)
async def create_message(
    chat_id: int = Form(...),
    from_user_id: int = Form(...),
    text: Optional[str] = Form(None),
    files: Optional[List[UploadFile]] = File(None),
    message_type: str = Form("text"),  # Default to "text", can be "voice" for voice messages
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new message with optional parameters:
    - For text messages: provide text and optionally files
    - For voice messages: provide audio file with no text
    
    Both types will have emotion analysis if from a patient.
    """
    # Validate message_type
    if message_type not in ["text", "voice"]:
        raise HTTPException(status_code=400, detail="Message type must be either 'text' or 'voice'")
    
    # Validate input based on message type
    if message_type == "text" and not text:
        raise HTTPException(status_code=400, detail="Text messages require text content")
    
    if message_type == "voice" and (not files or not any(file.filename for file in files)):
        raise HTTPException(status_code=400, detail="Voice messages require an audio file")
    
    # Create the message first
    message_create = MessageCreate(
        from_user_id=from_user_id,
        chat_id=chat_id,
        text=text if text else "",  # Empty string for voice messages
        status=False
    )
    
    # First upload any files if present
    file_paths = []
    presigned_urls = []
    files_data = []
    
    if files and any(file.filename for file in files):
        for file in files:
            if file.filename:
                try:
                    logger.info(f"Uploading file {file.filename}")
                    # Upload file to MinIO
                    object_name = await minio_service.upload_file(
                        file, 
                        chat_id, 
                        0  # Temporary message_id, will be updated after message creation
                    )
                    file_paths.append(object_name)
                    
                    # Get file URL for response
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
    
    # Create the message with emotion analysis
    message = await MessageService.create_message(
        db=db, 
        message_create=message_create,
        message_type=message_type,
        file_paths=file_paths
    )
    
    # Update file paths with correct message ID if files were uploaded
    if file_paths:
        updated_file_paths = []
        updated_presigned_urls = []
        updated_files_data = []
        
        for i, file_path in enumerate(file_paths):
            try:
                # Replace temporary message_id with actual message_id in path
                new_path = file_path.replace(f"{chat_id}/0/", f"{chat_id}/{message.id}/")
                
                # Rename the object in MinIO
                minio_service.client.copy_object(
                    bucket_name=minio_service.client.bucket_name,
                    object_name=new_path,
                    source_object=file_path,
                    source_bucket=minio_service.client.bucket_name
                )
                
                # Delete the old object
                minio_service.delete_file(file_path)
                
                updated_file_paths.append(new_path)
                
                # Get updated URL
                file_url = minio_service.get_file_url(new_path)
                updated_presigned_urls.append(file_url)
                
                # Update file data
                files_data[i]["file_path"] = new_path
                files_data[i]["file_url"] = file_url
                updated_files_data.append(files_data[i])
                
            except Exception as e:
                logger.error(f"Error updating file path: {str(e)}")
                # Keep the original path if update fails
                updated_file_paths.append(file_path)
                updated_presigned_urls.append(presigned_urls[i])
                updated_files_data.append(files_data[i])
        
        # Update message with corrected file paths
        message_update = MessageUpdate(media=",".join(updated_file_paths))
        message = await MessageService.update_message(
            db=db, 
            message_id=message.id, 
            message_update=message_update,
            message_type=message_type,
            file_paths=updated_file_paths
        )
        
        # Update response fields
        message.media = ",".join(updated_presigned_urls)
        message.files = updated_files_data
    
    return message

# Rest of the routes remain unchanged
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
                        if ext in ["mp3", "wav", "ogg", "m4a"]:
                            content_type = f"audio/{ext}"
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
    Update a message with optional new voice files
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
    voice_file_path = None
    
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
                    if ext in ["mp3", "wav", "ogg", "m4a"]:
                        content_type = f"audio/{ext}"
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
                # Check if file is an allowed audio file
                file_ext = os.path.splitext(file.filename)[1].lower()
                if file_ext not in ALLOWED_AUDIO_EXTENSIONS:
                    logger.warning(f"Rejected non-audio file upload: {file.filename}")
                    continue
                
                try:
                    # Upload file to MinIO
                    object_name = await minio_service.upload_file(
                        file, 
                        message.chat_id, 
                        message_id
                    )
                    new_file_paths.append(object_name)
                    voice_file_path = object_name
                    
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
                    logger.error(f"Error uploading new voice file {file.filename}: {str(e)}")
                    # Continue with other files if one fails
                    continue
    
    # Combine existing and new file paths
    all_file_paths = existing_file_paths + new_file_paths
    if all_file_paths:
        update_data["media"] = ",".join([p for p in all_file_paths if p.strip()])
    
    # Process new voice message through emotion service if available
    if voice_file_path:
        try:
            # Get voice file URL
            voice_url = minio_service.get_file_url(voice_file_path)
            
            # Analyze emotions from voice file
            update_data["emotional_state"] = emotion_service.analyze_voice_sentiment(voice_url)
            update_data["emotion"] = emotion_service.classify_voice_emotion(voice_url)
            
            logger.info(f"Voice emotion analysis: state={update_data['emotional_state']}, emotion={update_data['emotion']}")
        except Exception as e:
            logger.error(f"Error analyzing voice emotions: {str(e)}")
    
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
                                if ext in ["mp3", "wav", "ogg", "m4a"]:
                                    content_type = f"audio/{ext}"
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