import grpc.aio
from AuthTools import HeaderUser
from AuthTools.Permissions.dependencies import require_permissions
from fastapi import APIRouter, Depends, Body
from pydantic import BaseModel
from rfc9457 import NotFoundProblem, BadRequestProblem
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from fastapi_pagination.ext.sqlalchemy import paginate
from app.config import Permissions
from app.core.logger import logger
from app.core.utils import get_cheapest_terminal_prices, create_pagination_page
from app.database.crud import OrderService
from app.database.db.session import get_async_db
from app.database.schemas import OrderCreate, OrderRead, InvoiceItemCreate, OrderUpdate
from app.routers.private.v1 import choose_destination, custom_invoice, invoice_items, invoice, status
from app.services.user_info import fetch_user_identity
from app.rpc_client.calculator import CalculatorRpcClient, DetailedInfoService
from app.schemas.order import OrderIn


order_router = APIRouter(prefix="/order")
order_router.include_router(choose_destination.choose_destination_router)
order_router.include_router(custom_invoice.custom_invoice_router)
order_router.include_router(invoice_items.invoice_items_router)
order_router.include_router(invoice.invoice_router)
order_router.include_router(status.status_router)



@order_router.post("", response_model=OrderRead,
             description=f"Create order, required permissions: {Permissions.ORDER_ALL_WRITE.value}",
             dependencies=[Depends(require_permissions(Permissions.ORDER_ALL_WRITE))])
async def create_order(data: OrderIn = Body(...), db: AsyncSession = Depends(get_async_db)):
    order_service = OrderService(db)

    if await order_service.exists_by_lot_id(data.lot_id):
        raise BadRequestProblem("Order with this lot_id already exists")

    if await order_service.exists_by_vin(data.vin):
        raise BadRequestProblem("Order with this VIN already exists")

    try:
        user_identity = await fetch_user_identity(data.user_uuid)
    except grpc.aio.AioRpcError as e:
        logger.error(
            "Auth service failed while validating user for order creation",
            extra={
                "user_uuid": data.user_uuid,
                "status_code": e.code().name if e.code() else None,
                "details": e.details(),
            },
        )
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise NotFoundProblem(e.details())
        raise BadRequestProblem(e.details())

    try:
        async with DetailedInfoService() as detailed_info_service:
            location_data = await detailed_info_service.get_detailed_location(location_id=data.location_id)
            fee_type_data = await detailed_info_service.get_detailed_fee_type(fee_type_id=data.fee_type_id)
            destination_data = await detailed_info_service.get_detailed_destination(destination_id=data.destination_id)
    except grpc.aio.AioRpcError as e:
        logger.error(
            "Detailed info service failed during order creation",
            extra={
                "location_id": data.location_id,
                "fee_type_id": data.fee_type_id,
                "destination_id": data.destination_id,
                "status_code": e.code().name if e.code() else None,
                "details": e.details(),
            },
        )
        if e.code() == grpc.StatusCode.NOT_FOUND:
            raise NotFoundProblem(e.details())
        raise BadRequestProblem(e.details())

    async with CalculatorRpcClient() as calculator_client:
        try:
            calculator_data = await calculator_client.get_calculator_with_data(
                price=data.vehicle_value,
                auction=data.auction,
                vehicle_type=data.vehicle_type,
                location=location_data.name,
                fee_type=fee_type_data.fee_type,
                destination=destination_data.name,
            )
        except grpc.aio.AioRpcError as e:
            logger.error(
                "Calculator service failed during order creation",
                extra={
                    "location": location_data.name,
                    "fee_type": fee_type_data.fee_type,
                    "destination": destination_data.name,
                    "status_code": e.code().name if e.code() else None,
                    "details": e.details(),
                },
            )
            if e.code() == grpc.StatusCode.NOT_FOUND:
                raise NotFoundProblem(e.details())
            raise BadRequestProblem(e.details())

    detailed_data = calculator_data.detailed_data
    if not detailed_data:
        raise BadRequestProblem("Calculator response missing detailed data")

    terminal_name = next(
        (terminal.terminal_name for terminal in detailed_data.terminals if terminal.terminal_id == data.terminal_id),
        None,
    )
    if not terminal_name:
        raise NotFoundProblem("Terminal not found")

    destination_name = next(
        (
            destination.destination_name
            for destination in detailed_data.available_destinations
            if destination.destination_id == data.destination_id
        ),
        destination_data.name,
    )


    try:
        order = await order_service.create(
            OrderCreate(
                **data.model_dump(exclude={"user_name", "user_email"}),
                location_name=location_data.name,
                location_city=location_data.city,
                location_state=location_data.state,
                location_postal_code=location_data.postal_code,
                destination_name=destination_name,
                terminal_name=terminal_name,
                fee_type_name=fee_type_data.fee_type,
                user_name=user_identity["user_name"],
                user_email=user_identity["user_email"]
            ), flush=True
        )
        default_calculator = calculator_data.data.calculator
        if not default_calculator:
            raise BadRequestProblem("Calculator response missing calculator data")
        items = [
            InvoiceItemCreate(
                name=f'{data.vehicle_name} ({data.vin})',
                amount=data.vehicle_value,
                order_id=order.id,
            ),
            InvoiceItemCreate(name='Broker Fee', amount=default_calculator.broker_fee, order_id=order.id),
        ]
        items.extend(
            InvoiceItemCreate(name=fee.name, amount=fee.price, order_id=order.id)
            for fee in default_calculator.additional.fees
            if fee.price
        )

        cheapest_terminal = get_cheapest_terminal_prices(default_calculator)
        if cheapest_terminal:
            transportation_city, ocean_city = cheapest_terminal
            terminal_name = transportation_city.name
            items.append(
                InvoiceItemCreate(
                    name=f"Transportation ({terminal_name})",
                    amount=transportation_city.price,
                    order_id=order.id,
                )
            )
            items.append(
                InvoiceItemCreate(
                    name=f"Ocean Shipping ({terminal_name})",
                    amount=ocean_city.price,
                    order_id=order.id,
                )
            )

        await order_service.create_invoice_items_batch(order.id, items)

        await db.commit()

    except IntegrityError:
        logger.error(
            "Integrity error while creating order",
            extra={"lot_id": data.lot_id, "vin": data.vin},
        )
        await db.rollback()
        raise BadRequestProblem("Order already exists")
    return order


@order_router.put(
    "/{order_id}",
    response_model=OrderRead,
    description=f"Update order, required permissions: {Permissions.ORDER_ALL_WRITE.value}",
    dependencies=[Depends(require_permissions(Permissions.ORDER_ALL_WRITE))],
)
async def update_order(
    order_id: int,
    data: OrderUpdate = Body(...),
    db: AsyncSession = Depends(get_async_db),
):
    order_service = OrderService(db)
    order = await order_service.get_with_not_found_exception(order_id, "Order")
    update_data = data.model_dump(exclude_unset=True, exclude={"user_name", "user_email"})

    if "lot_id" in update_data and update_data["lot_id"] != order.lot_id:
        if await order_service.exists_by_lot_id(update_data["lot_id"]):
            raise BadRequestProblem("Order with this lot_id already exists")

    if "vin" in update_data and update_data["vin"] != order.vin:
        if await order_service.exists_by_vin(update_data["vin"]):
            raise BadRequestProblem("Order with this VIN already exists")

    if "user_uuid" in update_data and update_data["user_uuid"] != order.user_uuid:
        try:
            user_identity = await fetch_user_identity(update_data["user_uuid"])
            update_data.update(
                user_name=user_identity["user_name"],
                user_email=user_identity["user_email"],
            )
        except grpc.aio.AioRpcError as e:
            logger.error(
                "Auth service failed while updating user for order",
                extra={
                    "order_id": order_id,
                    "user_uuid": update_data["user_uuid"],
                    "status_code": e.code().name if e.code() else None,
                    "details": e.details(),
                },
            )
            if e.code() == grpc.StatusCode.NOT_FOUND:
                raise NotFoundProblem(e.details())
            raise BadRequestProblem(e.details())

    should_refresh_calculator_fields = any(
        field in update_data for field in ("location_id", "fee_type_id", "vehicle_value", "auction", "vehicle_type")
    )
    calculator_data = None
    terminal_name = None
    if should_refresh_calculator_fields:
        location_id = update_data.get("location_id", order.location_id)
        fee_type_id = update_data.get("fee_type_id", order.fee_type_id)
        try:
            async with DetailedInfoService() as detailed_info_service:
                location_data = await detailed_info_service.get_detailed_location(location_id=location_id)
                fee_type_data = await detailed_info_service.get_detailed_fee_type(fee_type_id=fee_type_id)
        except grpc.aio.AioRpcError as e:
            logger.error(
                "Detailed info service failed during order update",
                extra={
                    "order_id": order_id,
                    "location_id": location_id,
                    "fee_type_id": fee_type_id,
                    "status_code": e.code().name if e.code() else None,
                    "details": e.details(),
                },
            )
            if e.code() == grpc.StatusCode.NOT_FOUND:
                raise NotFoundProblem(e.details())
            raise BadRequestProblem(e.details())

        async with CalculatorRpcClient() as calculator_client:
            try:
                calculator_data = await calculator_client.get_calculator_with_data(
                    price=update_data.get("vehicle_value", order.vehicle_value),
                    auction=update_data.get("auction", order.auction),
                    vehicle_type=update_data.get("vehicle_type", order.vehicle_type),
                    fee_type=fee_type_data.fee_type,
                    location=location_data.name,
                )
            except grpc.aio.AioRpcError as e:
                logger.error(
                    "Calculator service failed during order update",
                    extra={
                        "order_id": order_id,
                        "location": location_data.name,
                        "fee_type": fee_type_data.fee_type,
                        "status_code": e.code().name if e.code() else None,
                        "details": e.details(),
                    },
                )
                if e.code() == grpc.StatusCode.NOT_FOUND:
                    raise NotFoundProblem(e.details())
                raise BadRequestProblem(e.details())

        detailed_data = calculator_data.detailed_data
        if not detailed_data:
            raise BadRequestProblem("Calculator response missing detailed data")
        target_terminal_id = update_data.get("terminal_id", order.terminal_id)
        terminal_name_from_calc = next(
            (
                terminal.terminal_name
                for terminal in detailed_data.terminals
                if terminal.terminal_id == target_terminal_id
            ),
            None,
        )
        if target_terminal_id and not terminal_name_from_calc:
            raise NotFoundProblem("Terminal not found for the selected location")

        update_data.update(
            location_name=location_data.name,
            location_city=location_data.city,
            location_state=location_data.state,
            location_postal_code=location_data.postal_code,
            fee_type_name=fee_type_data.fee_type,
        )
        if terminal_name_from_calc:
            update_data["terminal_name"] = terminal_name_from_calc

    if "destination_id" in update_data:
        try:
            async with DetailedInfoService() as detailed_info_service:
                destination_data = await detailed_info_service.get_detailed_destination(
                    destination_id=update_data["destination_id"]
                )
            update_data["destination_name"] = destination_data.name
        except grpc.aio.AioRpcError as e:
            logger.error(
                "Detailed info service failed while updating destination",
                extra={
                    "order_id": order_id,
                    "destination_id": update_data["destination_id"],
                    "status_code": e.code().name if e.code() else None,
                    "details": e.details(),
                },
            )
            if e.code() == grpc.StatusCode.NOT_FOUND:
                raise NotFoundProblem("Destination not found")
            raise BadRequestProblem(e.details())

    if "terminal_id" in update_data:
        try:
            async with DetailedInfoService() as detailed_info_service:
                terminal_data = await detailed_info_service.get_detailed_terminal(terminal_id=update_data["terminal_id"])
            terminal_name = terminal_data.name
        except grpc.aio.AioRpcError as e:
            logger.error(
                "Detailed info service failed while updating terminal",
                extra={
                    "order_id": order_id,
                    "terminal_id": update_data["terminal_id"],
                    "status_code": e.code().name if e.code() else None,
                    "details": e.details(),
                },
            )
            if e.code() == grpc.StatusCode.NOT_FOUND:
                raise NotFoundProblem("Terminal not found")
            raise BadRequestProblem(e.details())

    if terminal_name:
        update_data["terminal_name"] = terminal_name

    try:
        updated_order = await order_service.update(order_id, OrderUpdate(**update_data))
    except IntegrityError:
        logger.error(
            "Integrity error while updating order",
            extra={"order_id": order_id, "lot_id": update_data.get("lot_id"), "vin": update_data.get("vin")},
        )
        await db.rollback()
        raise BadRequestProblem("Order already exists")

    if not updated_order:
        raise NotFoundProblem("Order not found")
    return updated_order


OrdersPage = create_pagination_page(OrderRead)

class OrderSearch(BaseModel):
    search: str | None = None


@order_router.get(
    "/my",
    response_model=OrdersPage,
    description=f"Get user's own orders, required permissions: {Permissions.ORDER_OWN_READ.value}",
)
async def get_user_orders(
    data: OrderSearch = Depends(),
    user: HeaderUser = Depends(require_permissions(Permissions.ORDER_OWN_READ)),
    db: AsyncSession = Depends(get_async_db),
):
    order_service = OrderService(db)
    stmt = await order_service.get_all_with_search(data.search, user_uuid=user.uuid)
    return await paginate(db, stmt)


@order_router.get(
    '',
    response_model=OrdersPage,
    description=f"Get all orders, required permissions: {Permissions.ORDER_ALL_READ.value}",
    dependencies=[Depends(require_permissions(Permissions.ORDER_ALL_READ))]
)
async def get_orders(data: OrderSearch = Depends(), db: AsyncSession = Depends(get_async_db)):
    order_service = OrderService(db)
    smtp = await order_service.get_all_with_search(data.search)
    return await paginate(db, smtp)


@order_router.get(
    "/{order_id}",
    response_model=OrderRead,
    description=f"Get order by id, required permissions: {Permissions.ORDER_ALL_READ.value}",
    dependencies=[Depends(require_permissions(Permissions.ORDER_ALL_READ))],
)
async def get_order(order_id: int, db: AsyncSession = Depends(get_async_db)):
    order_service = OrderService(db)
    return await order_service.get_with_not_found_exception(order_id, "Order")


@order_router.delete(
    "/{order_id}",
    description=f"Delete order, required permissions: {Permissions.ORDER_ALL_DELETE.value}",
    dependencies=[Depends(require_permissions(Permissions.ORDER_ALL_DELETE))],
)
async def delete_order(order_id: int, db: AsyncSession = Depends(get_async_db)):
    order_service = OrderService(db)
    deleted = await order_service.delete(order_id)
    if not deleted:
        raise NotFoundProblem("Order not found")
    return {"status": "deleted"}
