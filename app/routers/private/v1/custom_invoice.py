import grpc
import grpc.aio
from AuthTools import HeaderUser
from AuthTools.Permissions.dependencies import require_permissions, require_one_of_permissions
from fastapi import APIRouter, Depends
from rfc9457 import BadRequestProblem, ForbiddenProblem, NotFoundProblem
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Permissions
from app.database.crud import CustomInvoiceService, OrderService
from app.database.db.session import get_async_db
from app.database.schemas import CustomInvoiceCreate, CustomInvoiceRead, CustomInvoiceUpdate
from app.enums.custom_invoice_status import CustomInvoiceStatus
from app.enums.order import OrderStatusEnum
from app.routers.private.v1.status.get_order_mixin import get_order_with_check
from app.rpc_client.files import FilesRpcClient
from app.rpc_client.gen.python.files.v1.files_pb2 import FileVisibility, FileKind
from app.schemas.custom_invoice import PresignedUploadResponse, DownloadUrlResponse


async def _get_order_and_invoice(
    order_id: int,
    order_service: OrderService,
    custom_invoice_service: CustomInvoiceService,
):
    order = await order_service.get(order_id)
    if not order:
        raise NotFoundProblem(detail="Order not found")

    custom_invoice = await custom_invoice_service.get_by_order_id(order_id)
    if not custom_invoice:
        raise NotFoundProblem(detail="Custom invoice not found")

    return order, custom_invoice


custom_invoice_router = APIRouter(
    prefix="/{order_id}/custom-invoice-added",
    tags=["Custom Invoice"],
)


@custom_invoice_router.get(
    "/get-presigned-url",
    response_model=PresignedUploadResponse,
    description=(
        f"Get presigned upload url for custom invoice PDF (only PDF is accepted), "
        f"required permission: {Permissions.ORDER_ALL_WRITE.value}"
    ),
    dependencies=[Depends(require_permissions(Permissions.ORDER_ALL_WRITE))],
)
async def get_custom_invoice_presigned_url(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    order_service = OrderService(db)
    custom_invoice_service = CustomInvoiceService(db)

    order = await get_order_with_check(order_id, order_service, OrderStatusEnum.VEHICLE_IN_CUSTOM_AGENCY)

    existing_invoice = await custom_invoice_service.get_by_order_id(order_id)
    if existing_invoice and order.delivery_status == OrderStatusEnum.CUSTOM_INVOICE_ADDED:
        raise BadRequestProblem(detail="Custom invoice already exists for this order")

    async with FilesRpcClient() as client:
        presigned = await client.create_presigned_upload(
            file_name=f"{order.vin}_custom_invoice.pdf",
            mime_type="application/pdf",
            visibility=FileVisibility.FILE_VISIBILITY_PRIVATE,
            folder=order.vin,
            kind=FileKind.FILE_KIND_PDF,
        )

    if existing_invoice:
        await custom_invoice_service.update(
            existing_invoice.id,
            CustomInvoiceUpdate(
                file_id=presigned.file_id,
                order_id=order_id,
                status=CustomInvoiceStatus.PENDING,
            ),
        )
    else:
        await custom_invoice_service.create(
            CustomInvoiceCreate(
                file_id=presigned.file_id,
                order_id=order_id,
                status=CustomInvoiceStatus.PENDING,
            )
        )

    return PresignedUploadResponse(
        file_id=presigned.file_id,
        bucket=presigned.bucket,
        key=presigned.key,
        upload_url=presigned.upload_url,
        expires_in=presigned.expires_in,
        http_method=presigned.http_method,
        headers=dict(presigned.headers),
    )


@custom_invoice_router.get(
    "",
    response_model=DownloadUrlResponse,
    description=(
        f"Get latest custom invoice download url (available or pending), "
        f"required permissions: {Permissions.ORDER_OWN_READ.value} (owner) or {Permissions.ORDER_ALL_READ.value} (admin)"
    ),
)
async def get_custom_invoice(
    order_id: int,
    user: HeaderUser = Depends(
        require_one_of_permissions(Permissions.ORDER_OWN_READ, Permissions.ORDER_ALL_READ)
    ),
    db: AsyncSession = Depends(get_async_db),
):
    order_service = OrderService(db)
    custom_invoice_service = CustomInvoiceService(db)

    order, custom_invoice = await _get_order_and_invoice(order_id, order_service, custom_invoice_service)

    has_all_permissions = Permissions.ORDER_ALL_READ.value in user.permissions
    if not has_all_permissions:
        if order.user_uuid != user.uuid:
            raise ForbiddenProblem(detail="Not allowed")
        if order.delivery_status != OrderStatusEnum.CUSTOM_INVOICE_ADDED:
            raise BadRequestProblem(detail="Custom invoice is not available yet")

    if custom_invoice.status == CustomInvoiceStatus.PENDING:
        raise BadRequestProblem(detail="Custom invoice is not uploaded yet")

    try:
        async with FilesRpcClient() as client:
            download = await client.get_download_url(file_id=custom_invoice.file_id)
    except grpc.aio.AioRpcError as e:
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise NotFoundProblem(detail="Invoice file not found")
        raise BadRequestProblem(detail=e.details())

    return DownloadUrlResponse(
        file_id=download.file_id,
        download_url=download.download_url,
        expires_in=download.expires_in,
    )


@custom_invoice_router.delete(
    "",
    response_model=CustomInvoiceRead,
    description=(
        f"Delete uploaded custom invoice for an order, "
        f"required permission: {Permissions.ORDER_ALL_WRITE.value}"
    ),
    dependencies=[Depends(require_permissions(Permissions.ORDER_ALL_WRITE))],
)
async def delete_custom_invoice(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    order_service = OrderService(db)
    custom_invoice_service = CustomInvoiceService(db)

    _, custom_invoice = await _get_order_and_invoice(order_id, order_service, custom_invoice_service)

    custom_invoice_data = CustomInvoiceRead.model_validate(custom_invoice)
    await custom_invoice_service.delete(custom_invoice.id)
    return custom_invoice_data


@custom_invoice_router.delete(
    "/file/{file_id}",
    response_model=CustomInvoiceRead,
    description=(
        f"Delete uploaded custom invoice by file id, "
        f"required permission: {Permissions.ORDER_ALL_WRITE.value}"
    ),
    dependencies=[Depends(require_permissions(Permissions.ORDER_ALL_WRITE))],
)
async def delete_custom_invoice_by_file_id(
    order_id: int,
    file_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    order_service = OrderService(db)
    custom_invoice_service = CustomInvoiceService(db)

    order = await order_service.get(order_id)
    if not order:
        raise NotFoundProblem(detail="Order not found")

    custom_invoice = await custom_invoice_service.get_by_file_id(file_id)
    if not custom_invoice or custom_invoice.order_id != order_id:
        raise NotFoundProblem(detail="Custom invoice not found")

    custom_invoice_data = CustomInvoiceRead.model_validate(custom_invoice)
    await custom_invoice_service.delete(custom_invoice.id)
    return custom_invoice_data
