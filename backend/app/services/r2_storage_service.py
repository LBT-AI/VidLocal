import os
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError
from app.config import settings

logger = logging.getLogger(__name__)

R2_PREFIX = "facebook_tmp"


class R2StorageError(Exception):
    pass


class R2StorageService:
    def __init__(self):
        self._client = None
        self._enabled = settings.R2_ENABLED and bool(settings.R2_ACCESS_KEY_ID)

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _get_client(self):
        if self._client is None:
            if not self._enabled:
                raise R2StorageError("R2 is not configured")
            self._client = boto3.client(
                "s3",
                endpoint_url=settings.R2_ENDPOINT,
                aws_access_key_id=settings.R2_ACCESS_KEY_ID,
                aws_secret_access_key=settings.R2_SECRET_ACCESS_KEY,
                region_name=settings.R2_REGION,
                config=Config(signature_version="s3v4"),
            )
        return self._client

    def _bucket(self) -> str:
        return settings.R2_BUCKET

    def _key_for_job(self, job_id: str, filename: str) -> str:
        return f"{R2_PREFIX}/{job_id}/{filename}"

    def upload_file(self, local_path: str, job_id: str, filename: str = "source.mp4") -> str:
        if not os.path.exists(local_path):
            raise R2StorageError(f"File not found: {local_path}")
        key = self._key_for_job(job_id, filename)
        file_size = os.path.getsize(local_path)
        try:
            client = self._get_client()
            client.upload_file(local_path, self._bucket(), key)
            logger.info("R2 upload OK: %s (%d bytes)", key, file_size)
            return key
        except ClientError as e:
            raise R2StorageError(f"R2 upload failed for {key}: {e}") from e

    def delete_file(self, key: str) -> bool:
        try:
            client = self._get_client()
            client.delete_object(Bucket=self._bucket(), Key=key)
            logger.info("R2 delete OK: %s", key)
            return True
        except ClientError as e:
            logger.error("R2 delete failed for %s: %s", key, e)
            return False

    def delete_job_files(self, job_id: str) -> dict:
        prefix = self._key_for_job(job_id, "")
        deleted_count = 0
        total_bytes = 0
        try:
            client = self._get_client()
            paginator = client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self._bucket(), Prefix=prefix):
                objects = page.get("Contents", [])
                if not objects:
                    continue
                keys = [{"Key": obj["Key"]} for obj in objects]
                total_bytes += sum(obj.get("Size", 0) for obj in objects)
                client.delete_objects(
                    Bucket=self._bucket(),
                    Delete={"Objects": keys},
                )
                deleted_count += len(keys)
                for obj in objects:
                    logger.info("R2 delete: %s (%d bytes)", obj["Key"], obj.get("Size", 0))
            if deleted_count:
                logger.info("R2 cleanup: deleted %d objects (%d bytes) for prefix %s", deleted_count, total_bytes, prefix)
            return {"deleted": deleted_count, "bytes": total_bytes}
        except ClientError as e:
            logger.error("R2 delete_job_files failed for %s: %s", prefix, e)
            return {"deleted": 0, "bytes": 0, "error": str(e)}

    def list_old_objects(self, older_than_days: int) -> list:
        prefix = f"{R2_PREFIX}/"
        cutoff = datetime.now(timezone.utc) - timedelta(days=older_than_days)
        old_objects = []
        try:
            client = self._get_client()
            paginator = client.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self._bucket(), Prefix=prefix):
                for obj in page.get("Contents", []):
                    last_modified = obj["LastModified"].replace(tzinfo=timezone.utc)
                    if last_modified < cutoff:
                        old_objects.append({
                            "key": obj["Key"],
                            "size": obj.get("Size", 0),
                            "last_modified": last_modified.isoformat(),
                        })
            return old_objects
        except ClientError as e:
            logger.error("R2 list_old_objects failed: %s", e)
            return []

    def delete_objects(self, objects: list) -> dict:
        if not objects:
            return {"deleted": 0, "bytes": 0}
        deleted_count = 0
        total_bytes = 0
        try:
            client = self._get_client()
            keys = [{"Key": obj["key"]} for obj in objects]
            total_bytes = sum(obj.get("size", 0) for obj in objects)
            client.delete_objects(
                Bucket=self._bucket(),
                Delete={"Objects": keys},
            )
            deleted_count = len(keys)
            logger.info("R2 bulk delete: %d objects, %d bytes", deleted_count, total_bytes)
            return {"deleted": deleted_count, "bytes": total_bytes}
        except ClientError as e:
            logger.error("R2 bulk delete failed: %s", e)
            return {"deleted": 0, "bytes": 0, "error": str(e)}


r2_storage = R2StorageService()
