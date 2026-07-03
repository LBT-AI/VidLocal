import os
import shutil
import uuid
from pathlib import Path
from typing import Optional
import boto3
from botocore.config import Config
from app.config import settings


class StorageService:
    def __init__(self):
        self.provider = settings.STORAGE_PROVIDER
        self.local_dir = Path(settings.PROJECT_DATA_DIR)
        self.local_dir.mkdir(parents=True, exist_ok=True)
        if self.provider == "s3":
            self.s3 = boto3.client(
                "s3",
                endpoint_url=settings.S3_ENDPOINT,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                config=Config(signature_version="s3v4"),
            )
            self.bucket = settings.S3_BUCKET

    def get_project_dir(self, project_id: uuid.UUID) -> Path:
        project_dir = self.local_dir / str(project_id)
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    def save_upload(self, project_id: uuid.UUID, file_obj, filename: str) -> str:
        if self.provider == "local":
            project_dir = self.get_project_dir(project_id)
            dest = project_dir / filename
            with open(dest, "wb") as f:
                shutil.copyfileobj(file_obj, f)
            return str(dest)
        else:
            key = f"projects/{project_id}/{filename}"
            self.s3.upload_fileobj(file_obj, self.bucket, key)
            return f"{settings.S3_ENDPOINT}/{self.bucket}/{key}"

    def save_file(self, project_id: uuid.UUID, data: bytes, filename: str) -> str:
        if self.provider == "local":
            project_dir = self.get_project_dir(project_id)
            dest = project_dir / filename
            with open(dest, "wb") as f:
                f.write(data)
            return str(dest)
        else:
            key = f"projects/{project_id}/{filename}"
            self.s3.put_object(Bucket=self.bucket, Key=key, Body=data)
            return f"{settings.S3_ENDPOINT}/{self.bucket}/{key}"

    def read_file(self, project_id: uuid.UUID, filename: str) -> bytes:
        if self.provider == "local":
            path = self.get_project_dir(project_id) / filename
            with open(path, "rb") as f:
                return f.read()
        else:
            key = f"projects/{project_id}/{filename}"
            response = self.s3.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()

    def file_exists(self, project_id: uuid.UUID, filename: str) -> bool:
        if self.provider == "local":
            return (self.get_project_dir(project_id) / filename).exists()
        else:
            key = f"projects/{project_id}/{filename}"
            try:
                self.s3.head_object(Bucket=self.bucket, Key=key)
                return True
            except:
                return False

    def delete_project(self, project_id: uuid.UUID):
        if self.provider == "local":
            project_dir = self.get_project_dir(project_id)
            if project_dir.exists():
                shutil.rmtree(project_dir)
        else:
            prefix = f"projects/{project_id}/"
            paginator = self.s3.get_paginator("list_objects_v2")
            for page in paginator.paginate(Bucket=self.bucket, Prefix=prefix):
                keys = [obj["Key"] for obj in page.get("Contents", [])]
                if keys:
                    self.s3.delete_objects(
                        Bucket=self.bucket,
                        Delete={"Objects": [{"Key": k} for k in keys]}
                    )


storage = StorageService()
