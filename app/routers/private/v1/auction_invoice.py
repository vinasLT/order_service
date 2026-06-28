from AuthTools.Permissions.dependencies import require_permissions
from fastapi import APIRouter, Depends
from rfc9457 import BadRequestProblem, NotFoundProblem
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Permissions
from app.database.crud import AuctionInvoiceService, OrderService
from app.database.db.session import get_async_db
from app.database.schemas import AuctionInvoiceCreate, AuctionInvoiceRead, AuctionInvoiceUpdate
from app.enums.custom_invoice_status import FileInvoiceStatus
from app.enums.order import OrderStatusEnum
from app.routers.private.v1.status.get_order_mixin import get_order_with_check
from app.rpc_client.files import FilesRpcClient
from app.rpc_client.gen.python.files.v1.files_pb2 import FileKind, FileVisibility
from app.schemas.custom_invoice import PresignedUploadResponse


async def _get_order_and_invoice(
    order_id: int,
    order_service: OrderService,
    auction_invoice_service: AuctionInvoiceService,
):
    order = await order_service.get(order_id)
    if not order:
        raise NotFoundProblem(detail="Order not found")

    auction_invoice = await auction_invoice_service.get_by_order_id(order_id)
    if not auction_invoice:
        raise NotFoundProblem(detail="Auction invoice not found")

    return order, auction_invoice


auction_invoice_router = APIRouter(
    prefix="/{order_id}/auction-invoice",
    tags=["Auction Invoice"],
)


@auction_invoice_router.get(
    "/get-presigned-url",
    response_model=PresignedUploadResponse,
    description=(
        f"Get presigned upload url for auction invoice PDF (only PDF is accepted), "
        f"required permission: {Permissions.ORDER_ALL_WRITE.value}"
    ),
    dependencies=[Depends(require_permissions(Permissions.ORDER_ALL_WRITE))],
)
async def get_auction_invoice_presigned_url(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    order_service = OrderService(db)
    auction_invoice_service = AuctionInvoiceService(db)

    order = await get_order_with_check(order_id, order_service, OrderStatusEnum.PORT_CHOSEN)

    existing_invoice = await auction_invoice_service.get_by_order_id(order_id)
    if existing_invoice and order.delivery_status == OrderStatusEnum.INVOICE_ADDED:
        raise BadRequestProblem(detail="Auction invoice already exists for this order")

    async with FilesRpcClient() as client:
        presigned = await client.create_presigned_upload(
            file_name=f"{order.vin}_auction_invoice.pdf",
            mime_type="application/pdf",
            visibility=FileVisibility.FILE_VISIBILITY_PRIVATE,
            folder=order.vin,
            kind=FileKind.FILE_KIND_PDF,
        )

    if existing_invoice:
        await auction_invoice_service.update(
            existing_invoice.id,
            AuctionInvoiceUpdate(
                file_id=presigned.file_id,
                order_id=order_id,
                status=FileInvoiceStatus.PENDING,
            ),
        )
    else:
        await auction_invoice_service.create(
            AuctionInvoiceCreate(
                file_id=presigned.file_id,
                order_id=order_id,
                status=FileInvoiceStatus.PENDING,
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


@auction_invoice_router.delete(
    "",
    response_model=AuctionInvoiceRead,
    description=(
        f"Delete uploaded auction invoice for an order, "
        f"required permission: {Permissions.ORDER_ALL_WRITE.value}"
    ),
    dependencies=[Depends(require_permissions(Permissions.ORDER_ALL_WRITE))],
)
async def delete_auction_invoice(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    order_service = OrderService(db)
    auction_invoice_service = AuctionInvoiceService(db)

    _, auction_invoice = await _get_order_and_invoice(
        order_id, order_service, auction_invoice_service
    )

    auction_invoice_data = AuctionInvoiceRead.model_validate(auction_invoice)
    await auction_invoice_service.delete(auction_invoice.id)
    return auction_invoice_data


@auction_invoice_router.delete(
    "/file/{file_id}",
    response_model=AuctionInvoiceRead,
    description=(
        f"Delete uploaded auction invoice by file id, "
        f"required permission: {Permissions.ORDER_ALL_WRITE.value}"
    ),
    dependencies=[Depends(require_permissions(Permissions.ORDER_ALL_WRITE))],
)
async def delete_auction_invoice_by_file_id(
    order_id: int,
    file_id: int,
    db: AsyncSession = Depends(get_async_db),
):
    order_service = OrderService(db)
    auction_invoice_service = AuctionInvoiceService(db)

    order = await order_service.get(order_id)
    if not order:
        raise NotFoundProblem(detail="Order not found")

    auction_invoice = await auction_invoice_service.get_by_file_id(file_id)
    if not auction_invoice or auction_invoice.order_id != order_id:
        raise NotFoundProblem(detail="Auction invoice not found")

    auction_invoice_data = AuctionInvoiceRead.model_validate(auction_invoice)
    await auction_invoice_service.delete(auction_invoice.id)
    return auction_invoice_data
