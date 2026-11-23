from dataclasses import dataclass
from urllib.parse import quote

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi.responses import Response

from app.core.config import settings


class DocumentStorageError(RuntimeError):
    pass


@dataclass(frozen=True)
class StoredDocument:
    content: bytes
    content_type: str


def attachment_response(document: StoredDocument, filename: str) -> Response:
    safe_name = filename.replace("\\", "/").rsplit("/", 1)[-1].replace("\r", "").replace("\n", "")
    encoded_name = quote(safe_name or "patient-record")
    return Response(
        content=document.content,
        media_type=document.content_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_name}",
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, no-store",
        },
    )


class S3DocumentStorage:
    def __init__(self) -> None:
        if not settings.s3_bucket:
            raise DocumentStorageError("S3_BUCKET is not configured.")
        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            region_name=settings.aws_region,
            endpoint_url=settings.s3_endpoint_url,
        )

    def put(self, key: str, content: bytes, content_type: str) -> None:
        encryption: dict[str, str] = {"ServerSideEncryption": "AES256"}
        if settings.s3_kms_key_id:
            encryption = {
                "ServerSideEncryption": "aws:kms",
                "SSEKMSKeyId": settings.s3_kms_key_id,
            }
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
                **encryption,
            )
        except (BotoCoreError, ClientError) as exc:
            raise DocumentStorageError("Unable to store the patient document in S3.") from exc

    def get(self, key: str) -> StoredDocument:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return StoredDocument(
                content=response["Body"].read(),
                content_type=response.get("ContentType", "application/octet-stream"),
            )
        except (BotoCoreError, ClientError, KeyError) as exc:
            raise DocumentStorageError("Unable to retrieve the patient document from S3.") from exc

    def delete(self, key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except (BotoCoreError, ClientError) as exc:
            raise DocumentStorageError("Unable to remove the patient document from S3.") from exc
