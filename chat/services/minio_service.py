import os
import uuid
from minio import Minio
from minio.error import S3Error
from fastapi import UploadFile, HTTPException
import io
import aiofiles
import logging
from typing import Optional, List, Tuple
from datetime import timedelta
import urllib3

from core.config import settings

logger = logging.getLogger(__name__)

class MinioService:
    def __init__(self):
        
        http_client = None
        if settings.MINIO_PROXY_URL:  # Если указан прокси
            http_client = urllib3.ProxyManager(
                proxy_url=settings.MINIO_PROXY_URL,
                timeout=urllib3.Timeout(connect=10.0, read=30.0)  # Таймауты для соединения и чтения
            )
        else:
            http_client = urllib3.PoolManager(
                timeout=urllib3.Timeout(connect=10.0, read=30.0)
            )

        # Инициализация MinIO клиента
        self.client = Minio(
            settings.MINIO_URL,
            access_key=settings.MINIO_ROOT_USER,
            secret_key=settings.MINIO_ROOT_PASSWORD,
            secure=settings.MINIO_SECURE,
            http_client=http_client  # Передаем HTTP-клиент
        )

        # Инициализация бакета
        self._initialize_bucket()
    
    def _initialize_bucket(self):
        """Initialize the MinIO bucket if it doesn't exist"""
        try:
            if not self.client.bucket_exists(settings.MINIO_BUCKET_NAME):
                self.client.make_bucket(settings.MINIO_BUCKET_NAME)
                logger.info(f"Created bucket: {settings.MINIO_BUCKET_NAME}")
            else:
                logger.info(f"Bucket {settings.MINIO_BUCKET_NAME} already exists")
        except S3Error as e:
            logger.error(f"Error initializing MinIO bucket: {e}")
            raise

    async def upload_file(self, file: UploadFile, chat_id: int, message_id: int) -> str:
        """
        Upload a file to MinIO and return the path
        
        Args:
            file: The file to upload
            chat_id: The ID of the chat
            message_id: The ID of the message
            
        Returns:
            str: The path to the uploaded file in MinIO
        """
        try:
            # Generate a unique filename
            original_filename = file.filename
            file_extension = os.path.splitext(original_filename)[1] if original_filename else ""
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            
            # Create the object name with path: chat_id/message_id/filename
            object_name = f"{chat_id}/{message_id}/{unique_filename}"
            
            # Read file content
            content = await file.read()
            
            # Upload file to MinIO
            self.client.put_object(
                bucket_name=settings.MINIO_BUCKET_NAME,
                object_name=object_name,
                data=io.BytesIO(content),
                length=len(content),
                content_type=file.content_type
            )
            
            return object_name
        except S3Error as e:
            logger.error(f"Error uploading file to MinIO: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error uploading file: {e}")
            raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

    def get_file_url(self, object_name: str) -> str:
        """
        Get the URL for a file in MinIO
        
        Args:
            object_name: The name of the object in MinIO
            
        Returns:
            str: The URL to access the file
        """
        try:
            # Check if object exists
            self.client.stat_object(settings.MINIO_BUCKET_NAME, object_name)
            
            # Generate presigned URL (valid for 1 hour)
            # Use timedelta object instead of an integer for expires
            url = self.client.presigned_get_object(
                bucket_name=settings.MINIO_BUCKET_NAME,
                object_name=object_name,
                expires=timedelta(hours=1)  # Use timedelta instead of integer
            )
            
            return url
        except S3Error as e:
            logger.error(f"Error getting file URL from MinIO: {e}")
            raise HTTPException(status_code=404, detail="File not found")

    def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from MinIO
        
        Args:
            object_name: The name of the object in MinIO
            
        Returns:
            bool: True if successful
        """
        try:
            self.client.remove_object(settings.MINIO_BUCKET_NAME, object_name)
            return True
        except S3Error as e:
            logger.error(f"Error deleting file from MinIO: {e}")
            return False
    
    def list_files(self, chat_id: int, message_id: Optional[int] = None) -> List[str]:
        """
        List files for a chat or specific message
        
        Args:
            chat_id: The ID of the chat
            message_id: Optional ID of the message
            
        Returns:
            List[str]: List of object names
        """
        try:
            prefix = f"{chat_id}/"
            if message_id:
                prefix = f"{chat_id}/{message_id}/"
            
            objects = self.client.list_objects(settings.MINIO_BUCKET_NAME, prefix=prefix, recursive=True)
            return [obj.object_name for obj in objects]
        except S3Error as e:
            logger.error(f"Error listing files from MinIO: {e}")
            return []

# Singleton instance
minio_service = MinioService()