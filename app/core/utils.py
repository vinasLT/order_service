from pathlib import Path

from fastapi import Query
from fastapi_pagination import Page
from fastapi_pagination.customization import CustomizedPage, UseParamsFields, UseFieldsAliases
from pydantic import BaseModel

from app.enums.order import OrderStatusEnum
from app.rpc_client.gen.python.calculator.v1 import calculator_pb2
from app.rpc_client.gen.python.calculator.v1.calculator_pb2 import City

BASE_DIR = Path(__file__).resolve().parent.parent.parent

_LEGACY_GENERATED_INVOICE_STATUSES = (
    OrderStatusEnum.INVOICE_ADDED,
    OrderStatusEnum.TRACKING_ADDED,
    OrderStatusEnum.VEHICLE_IN_CUSTOM_AGENCY,
    OrderStatusEnum.CUSTOM_INVOICE_ADDED,
    OrderStatusEnum.DELIVERED,
)


def uses_legacy_generated_invoice(
    delivery_status: OrderStatusEnum,
    has_auction_invoice: bool,
) -> bool:
    return not has_auction_invoice and delivery_status in _LEGACY_GENERATED_INVOICE_STATUSES



def get_transportation_options(calculator) -> dict[str, City]:
    """Index transportation options by name, keeping only valid prices."""
    return {
        entry.name: entry
        for entry in getattr(calculator, "transportation_price", [])
        if entry.name and entry.price > 0
    }


def get_ocean_options(calculator) -> dict[str, City]:
    """Index ocean shipping options by name, keeping only valid prices."""
    return {
        entry.name: entry
        for entry in getattr(calculator, "ocean_ship", [])
        if entry.name and entry.price > 0
    }


def get_cheapest_terminal_prices(calculator: calculator_pb2.DefaultCalculator) -> tuple[City, City] | None:
    """
    Returns (transportation_city, ocean_city) for the cheapest transportation + ocean combo.
    Ignores entries that miss either component.
    """
    transportation_options = get_transportation_options(calculator)
    ocean_options = get_ocean_options(calculator)

    cheapest_pair: tuple[City, City] | None = None
    cheapest_total: int | None = None

    for name, transportation_city in transportation_options.items():
        ocean_city = ocean_options.get(name)
        if ocean_city is None:
            continue

        total = transportation_city.price + ocean_city.price
        if cheapest_total is None or total < cheapest_total:
            cheapest_pair = (transportation_city, ocean_city)
            cheapest_total = total

    return cheapest_pair


def create_pagination_page(pydantic_model: type[BaseModel])-> type[Page[BaseModel]]:
    return CustomizedPage[
        Page[pydantic_model],
        UseParamsFields(size=Query(5, ge=1, le=1000)),
        UseFieldsAliases(
            items="data",
            total='count'
        )
    ]
