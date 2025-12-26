from io import BytesIO

import grpc.aio
from AuthTools import HeaderUser
from AuthTools.Permissions.dependencies import require_one_of_permissions
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from rfc9457 import ForbiddenProblem, NotFoundProblem, BadRequestProblem
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Permissions
from app.core.logger import logger
from app.database.crud import OrderService
from app.database.db.session import get_async_db
from app.database.models import Order
from app.enums.order import OrderStatusEnum
from app.rpc_client.auth import AuthRpcClient
from app.rpc_client.calculator import CalculatorRpcClient
from app.rpc_client.gen.python.calculator.v1 import calculator_pb2
from app.services.invoice_generator.generator import InvoiceGenerator


invoice_router = APIRouter(prefix="/{order_id}/invoice", tags=["Invoice"])


def _safe_rate(numerator: int, denominator: int) -> float | None:
    if not numerator or not denominator:
        return None
    return numerator / denominator


def _rate_from_city_lists(
    eur_cities: list[calculator_pb2.City],
    usd_cities: list[calculator_pb2.City],
) -> float | None:
    usd_by_name = {city.name: city.price for city in usd_cities if city.name and city.price}
    for city in eur_cities:
        usd_price = usd_by_name.get(city.name)
        if usd_price:
            return city.price / usd_price
    return None


def _extract_usd_to_eur_rate(
    calculator: calculator_pb2.GetCalculatorWithDataResponse,
) -> float | None:
    data = calculator.data
    if not data or not data.calculator or not data.eu_calculator:
        return None

    eur_calc = data.eu_calculator
    usd_calc = data.calculator

    rate = _safe_rate(eur_calc.broker_fee, usd_calc.broker_fee)
    if rate:
        return rate

    rate = _safe_rate(getattr(eur_calc.additional, "summ", 0), getattr(usd_calc.additional, "summ", 0))
    if rate:
        return rate

    for eur_list, usd_list in (
        (eur_calc.totals, usd_calc.totals),
        (eur_calc.transportation_price, usd_calc.transportation_price),
        (eur_calc.ocean_ship, usd_calc.ocean_ship),
    ):
        rate = _rate_from_city_lists(list(eur_list), list(usd_list))
        if rate:
            return rate

    return None


async def _get_usd_to_eur_rate(order: Order) -> float | None:
    try:
        async with CalculatorRpcClient() as calculator_client:
            calculator = await calculator_client.get_calculator_with_data(
                price=order.vehicle_value,
                auction=order.auction,
                vehicle_type=order.vehicle_type,
                location=order.location_name,
            )
    except grpc.aio.AioRpcError:
        logger.warning(
            "Calculator RPC failed while fetching USD/EUR rate",
            extra={"order_id": order.id},
        )
        return None
    rate = _extract_usd_to_eur_rate(calculator)
    if rate:
        logger.info(
            "USD/EUR rate resolved for invoice",
            extra={"order_id": order.id, "usd_to_eur_rate": rate},
        )
    else:
        logger.warning(
            "USD/EUR rate not available for invoice",
            extra={"order_id": order.id},
        )
    return rate


@invoice_router.get(
    "",
    description=f"Get invoice PDF for order\nRequired permissions: {Permissions.ORDER_OWN_READ.value}(for user)\n"
                f"{Permissions.ORDER_ALL_READ.value}(for admin)",
)
async def get_invoice(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    user: HeaderUser = Depends(require_one_of_permissions(Permissions.ORDER_OWN_READ, Permissions.ORDER_ALL_READ)),
):
    order_service = OrderService(db)
    order = await order_service.get(order_id)
    if not order:
        raise NotFoundProblem(detail="Order not found")

    has_all_orders_permission = Permissions.ORDER_ALL_READ.value in user.permissions
    is_order_owner = order.user_uuid == user.uuid

    if not has_all_orders_permission and not is_order_owner:
        raise ForbiddenProblem(detail="Not allowed")

    if order.delivery_status == OrderStatusEnum.WON:
        detail = (
            f"You need wait until status of order will be: {OrderStatusEnum.PORT_CHOSEN.value}"
            if has_all_orders_permission
            else "You need to choose port to see invoice"
        )
        raise BadRequestProblem(detail=detail)

    if order.delivery_status == OrderStatusEnum.PORT_CHOSEN and not has_all_orders_permission:
        raise BadRequestProblem(detail=f"You need wait until status of order will be: {OrderStatusEnum.INVOICE_ADDED.value}")

    auth_user = None
    try:
        async with AuthRpcClient() as auth_client:
            auth_user = await auth_client.get_user(user_uuid=order.user_uuid)
    except grpc.aio.AioRpcError:
        # Ignore RPC failures to avoid blocking invoice generation
        pass

    usd_to_eur_rate = await _get_usd_to_eur_rate(order)
    generator = InvoiceGenerator(order, user=auth_user, usd_to_eur_rate=usd_to_eur_rate)
    pdf_bytes = generator.generate_invoice_based_on_invoice_type()

    filename = f"invoice_{order.vin}.pdf"
    return StreamingResponse(
        BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename=\"{filename}\"'},
    )
