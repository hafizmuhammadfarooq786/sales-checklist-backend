"""
S3 upload service for audio files
Handles uploading files to AWS S3 bucket
"""
import boto3
from botocore.exceptions import ClientError
from pathlib import Path
from typing import Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


class S3Service:
    """Service for managing file uploads to S3"""

    def __init__(self):
        """Initialize S3 client"""
        self.s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION,
        )
        self.bucket_name = settings.AWS_S3_BUCKET_NAME

    def upload_file(
        self,
        file_path: str,
        s3_key: str,
        content_type: Optional[str] = None,
        bucket_name: Optional[str] = None,
    ) -> str:
        """
        Upload a file to S3

        Args:
            file_path: Local path to the file to upload
            s3_key: S3 object key (path in bucket)
            content_type: MIME type of the file
            bucket_name: Optional bucket name (uses default if not provided)

        Returns:
            S3 URL of the uploaded file

        Raises:
            Exception: If upload fails
        """
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            # Use provided bucket or default
            target_bucket = bucket_name or self.bucket_name

            # Upload file
            self.s3_client.upload_file(
                file_path,
                target_bucket,
                s3_key,
                ExtraArgs=extra_args,
            )

            # Generate S3 URL
            s3_url = f"https://{target_bucket}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"

            logger.info(f"Successfully uploaded file to S3: {s3_url}")
            return s3_url

        except ClientError as e:
            logger.error(f"Failed to upload file to S3: {e}")
            raise Exception(f"S3 upload failed: {str(e)}")

    def upload_fileobj(
        self,
        file_obj,
        s3_key: str,
        content_type: Optional[str] = None,
    ) -> str:
        """
        Upload a file-like object to S3

        Args:
            file_obj: File-like object to upload
            s3_key: S3 object key (path in bucket)
            content_type: MIME type of the file

        Returns:
            S3 URL of the uploaded file

        Raises:
            Exception: If upload fails
        """
        try:
            extra_args = {}
            if content_type:
                extra_args["ContentType"] = content_type

            # Upload file object
            self.s3_client.upload_fileobj(
                file_obj,
                self.bucket_name,
                s3_key,
                ExtraArgs=extra_args,
            )

            # Generate S3 URL
            s3_url = f"https://{self.bucket_name}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"

            logger.info(f"Successfully uploaded file object to S3: {s3_url}")
            return s3_url

        except ClientError as e:
            logger.error(f"Failed to upload file object to S3: {e}")
            raise Exception(f"S3 upload failed: {str(e)}")

    def delete_file(self, s3_key: str) -> bool:
        """
        Delete a file from S3

        Args:
            s3_key: S3 object key to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            self.s3_client.delete_object(
                Bucket=self.bucket_name,
                Key=s3_key,
            )
            logger.info(f"Successfully deleted file from S3: {s3_key}")
            return True

        except ClientError as e:
            logger.error(f"Failed to delete file from S3: {e}")
            return False

    def generate_presigned_url(
        self,
        s3_key: str,
        expiration: int = 3600,
        bucket_name: Optional[str] = None,
    ) -> Optional[str]:
        """
        Generate a presigned URL for temporary access to a file

        Args:
            s3_key: S3 object key
            expiration: URL expiration time in seconds (default 1 hour)
            bucket_name: Optional bucket name (uses default if not provided)

        Returns:
            Presigned URL or None if failed
        """
        try:
            # Use provided bucket or default
            target_bucket = bucket_name or self.bucket_name

            url = self.s3_client.generate_presigned_url(
                "get_object",
                Params={"Bucket": target_bucket, "Key": s3_key},
                ExpiresIn=expiration,
            )
            return url

        except ClientError as e:
            logger.error(f"Failed to generate presigned URL: {e}")
            return None

    def check_file_exists(self, s3_key: str) -> bool:
        """
        Check if a file exists in S3

        Args:
            s3_key: S3 object key to check

        Returns:
            True if file exists, False otherwise
        """
        try:
            self.s3_client.head_object(Bucket=self.bucket_name, Key=s3_key)
            return True
        except ClientError:
            return False


# Create singleton instance
s3_service = S3Service()


def get_s3_service() -> S3Service:
    """Get S3 service instance"""
    return s3_service
