from pydantic import BaseModel


class PresignedUploadResponse(BaseModel):
    file_id: int
    bucket: str
    key: str
    upload_url: str
    expires_in: int
    http_method: str
    headers: dict[str, str]


class DownloadUrlResponse(BaseModel):
    file_id: int
    download_url: str
    expires_in: int