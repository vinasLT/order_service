import os
import sys
from typing import Sequence

import grpc

from app.config import settings
from app.rpc_client.base_client import BaseRpcClient, T

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'gen', 'python'))

from app.rpc_client.gen.python.files.v1 import files_pb2, files_pb2_grpc


class FilesRpcClient(BaseRpcClient[files_pb2_grpc.FileServiceStub]):
    def __init__(self, server_url: str | None = None):
        # Use dedicated file service URL instead of the generic RPC API endpoint
        super().__init__(server_url=server_url or settings.RCP_FILE_URL)

    async def __aenter__(self):
        await self.connect()
        return self

    def _create_stub(self, channel: grpc.aio.Channel) -> T:
        return files_pb2_grpc.FileServiceStub(channel)

    async def create_presigned_upload(
        self,
        *,
        file_name: str,
        mime_type: str,
        visibility: files_pb2.FileVisibility,
        folder: str | None = None,
        kind: files_pb2.FileKind | None = None,
    ) -> files_pb2.CreatePresignedUploadResponse:
        request = files_pb2.CreatePresignedUploadRequest(
            file_name=file_name,
            mime_type=mime_type,
            visibility=visibility,
        )
        if folder is not None:
            request.folder = folder
        if kind is not None:
            request.kind = kind

        return await self._execute_request(self.stub.CreatePresignedUpload, request)

    async def create_presigned_upload_batch(
        self,
        *,
        file_name: str,
        mime_type: str,
        visibility: files_pb2.FileVisibility,
        amount_of_files: int,
        folder: str | None = None,
        kind: files_pb2.FileKind | None = None,
    ) -> files_pb2.CreatePresignedUploadBatchResponse:
        request = files_pb2.CreatePresignedUploadBatchRequest(
            file_name=file_name,
            mime_type=mime_type,
            visibility=visibility,
            amount_of_files=amount_of_files,
        )
        if folder is not None:
            request.folder = folder
        if kind is not None:
            request.kind = kind

        return await self._execute_request(self.stub.CreatePresignedUploadBatch, request)

    async def get_download_url(
        self,
        *,
        file_id: int,
        expires_in: int | None = None,
    ) -> files_pb2.GetDownloadUrlResponse:
        request = files_pb2.GetDownloadUrlRequest(file_id=file_id)
        if expires_in is not None:
            request.expires_in = expires_in

        return await self._execute_request(self.stub.GetDownloadUrl, request)

    async def get_batch_download_urls(
        self,
        *,
        file_ids: Sequence[int],
        expires_in: int | None = None,
    ) -> files_pb2.GetBatchDownloadUrlsResponse:
        request = files_pb2.GetBatchDownloadUrlsRequest(file_ids=file_ids)
        if expires_in is not None:
            request.expires_in = expires_in

        return await self._execute_request(self.stub.GetBatchDownloadUrls, request)
