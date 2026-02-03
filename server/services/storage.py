"""
ExamGuard Pro - Storage Service
Handles file uploads to S3-compatible storage or local filesystem
"""

import os
import aiobotocore.session
from botocore.exceptions import ClientError
from datetime import datetime
import uuid

# Configuration
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID", "minioadmin")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "minioadmin")
BUCKET_NAME = os.getenv("S3_BUCKET", "examguard-uploads")
ENDPOINT_URL = os.getenv("S3_ENDPOINT", "http://localhost:9000") # Default to local MinIO
REGION_NAME = os.getenv("AWS_REGION", "us-east-1")
USE_S3 = os.getenv("USE_S3", "false").lower() == "true"

class StorageService:
    def __init__(self):
        self.session = aiobotocore.session.get_session()
        
    async def upload_file(self, file_data: bytes, folder: str, content_type: str = "image/jpeg") -> str:
        """
        Upload file to storage and return public URL/path
        """
        filename = f"{folder}/{uuid.uuid4().hex}.jpg"
        
        if USE_S3:
            return await self._upload_s3(file_data, filename, content_type)
        else:
            return await self._upload_local(file_data, filename)

    async def _upload_s3(self, data: bytes, key: str, content_type: str) -> str:
        try:
            async with self.session.create_client(
                's3', 
                region_name=REGION_NAME,
                endpoint_url=ENDPOINT_URL,
                aws_access_key_id=AWS_ACCESS_KEY,
                aws_secret_access_key=AWS_SECRET_KEY
            ) as client:
                await client.put_object(
                    Bucket=BUCKET_NAME,
                    Key=key,
                    Body=data,
                    ContentType=content_type,
                    ACL='public-read'
                )
                # Return URL
                return f"{ENDPOINT_URL}/{BUCKET_NAME}/{key}"
        except Exception as e:
            print(f"S3 Upload Error: {e}")
            # Fallback to local
            return await self._upload_local(data, key)

    async def _upload_local(self, data: bytes, key: str) -> str:
        # Ensure directory exists
        path = os.path.join("uploads", key) # key includes folder prefix
        os.makedirs(os.path.dirname(path), exist_ok=True)
        
        # Write file
        with open(path, "wb") as f:
            f.write(data)
            
        return f"/uploads/{key}"

# Singleton
storage_service = StorageService()
