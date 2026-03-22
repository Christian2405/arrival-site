"""
Arrival Backend — S3 Upload Service
Async S3 operations via aiobotocore for spatial intelligence data capture.
"""

import logging
from datetime import datetime
from contextlib import asynccontextmanager

from aiobotocore.session import AioSession
from app.config import AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_S3_BUCKET, AWS_REGION

logger = logging.getLogger("arrival.s3")

_aio_session = AioSession()


@asynccontextmanager
async def _get_s3_client():
    """Yield an aiobotocore S3 client."""
    async with _aio_session.create_client(
        "s3",
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    ) as client:
        yield client


async def upload_clip(key: str, data: bytes, content_type: str = "video/mp4") -> str:
    """Upload video clip bytes to S3. Returns the S3 key."""
    try:
        async with _get_s3_client() as client:
            await client.put_object(
                Bucket=AWS_S3_BUCKET,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        logger.info(f"Uploaded clip to s3://{AWS_S3_BUCKET}/{key} ({len(data)} bytes)")
        return key
    except Exception as e:
        logger.error(f"S3 upload failed for {key}: {e}")
        raise


async def get_presigned_url(key: str, expires_in: int = 3600) -> str:
    """Generate a presigned download URL for a clip."""
    try:
        async with _get_s3_client() as client:
            url = await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": AWS_S3_BUCKET, "Key": key},
                ExpiresIn=expires_in,
            )
        return url
    except Exception as e:
        logger.error(f"Failed to generate presigned URL for {key}: {e}")
        raise


def build_s3_key(session_id: str, clip_id: str) -> str:
    """Build the S3 key path for a clip."""
    now = datetime.utcnow()
    return f"videos/{now.year}/{now.month:02d}/{now.day:02d}/{session_id}/{clip_id}.mp4"
