import asyncio
from datetime import datetime, timezone

from app.core.utils import get_cheapest_terminal_prices
from app.database.crud import OrderService
from app.database.db.session import get_db_context
from app.database.schemas import InvoiceItemCreate, OrderCreate
from app.enums.auction import AuctionEnum
from app.rpc_client.auction_api import ApiRpcClient
from app.rpc_client.calculator import CalculatorRpcClient
from app.rpc_client.gen.python.auction.v1.lot_pb2 import Lot
from app.rpc_client.gen.python.calculator.v1 import calculator_pb2


class GenerateFromLot:
    def __init__(self, lot_id: int, auction: AuctionEnum, user_uuid: str = "", bid_amount: int = 0):
        self.lot_id = lot_id
        self.auction = auction
        self.user_uuid = user_uuid
        self.bid_amount = bid_amount

    async def _get_lot(self) -> Lot:
        async with ApiRpcClient() as client:
            response = await client.get_lot_by_vin_or_lot_id(
                vin_or_lot_id=str(self.lot_id), site=self.auction.value
            )
        if not response.lot:
            raise ValueError("Lot not found")
        return response.lot[0]
    @staticmethod
    async def _get_calculator_data(
        lot: Lot, vehicle_value: int
    ) -> calculator_pb2.GetCalculatorWithDataResponse:
        async with CalculatorRpcClient() as client:
            calculator = await client.get_calculator_with_data(
                price=vehicle_value,
                auction=lot.base_site,
                vehicle_type="MOTO" if lot.vehicle_type == 'Motorcycle' else "CAR",
                location=lot.location,
            )
        return calculator

    async def generate(self):
        lot = await self._get_lot()
        vehicle_value = next(
            (
                value
                for value in [self.bid_amount, getattr(lot, "purchase_price", 0), getattr(lot, "current_bid", 0), getattr(lot, "price_future", 0), getattr(lot, "price_new", 0)]
                if value
            ),
            0,
        )
        calculator = await self._get_calculator_data(lot, vehicle_value)
        detailed_data = calculator.detailed_data
        if not detailed_data.terminals:
            raise ValueError("Calculator response missing terminals")
        if not detailed_data.available_destinations:
            raise ValueError("Calculator response missing destinations")

        terminal = detailed_data.terminals[0]
        destination = detailed_data.available_destinations[0]
        location = detailed_data.location_data
        fee_type_data = detailed_data.fee_type_data
        location_id = detailed_data.location_id or getattr(lot, "location_id", 0)
        terminal_id = terminal.terminal_id
        fee_type_id = detailed_data.fee_type_id or 0
        keys = str(lot.keys).lower() == "yes"
        damage = bool(lot.damage_pr or lot.damage_sec)
        default_calculator = calculator.data.calculator
        if not default_calculator:
            raise ValueError("Calculator response missing calculator data")

        transportation_city = None
        ocean_city = None
        terminal_name_for_order = terminal.terminal_name
        terminal_id_for_order = terminal_id
        cheapest_terminal = get_cheapest_terminal_prices(default_calculator)
        if cheapest_terminal:
            transportation_city, ocean_city = cheapest_terminal
            terminal_name_for_order = transportation_city.name
            matching_terminal = next(
                (t for t in detailed_data.terminals if t.terminal_name == terminal_name_for_order),
                None,
            )
            if matching_terminal:
                terminal_id_for_order = matching_terminal.terminal_id
        async with get_db_context() as db:
            order_service = OrderService(db)
            if await order_service.exists_by_lot_id(lot.lot_id):
                raise ValueError("Order with this lot_id already exists")
            if await order_service.exists_by_vin(lot.vin):
                raise ValueError("Order with this VIN already exists")

            order = await order_service.create(
                OrderCreate(
                    auction=self.auction,
                    order_date=datetime.now(timezone.utc),
                    lot_id=lot.lot_id,
                    vehicle_value=vehicle_value,
                    vehicle_type="MOTO" if lot.vehicle_type == 'Motorcycle' else "CAR",
                    vin=lot.vin,
                    vehicle_name=lot.title,
                    keys=keys,
                    damage=damage,
                    color=lot.color or "Unknown",
                    auto_generated=True,
                    fee_type=fee_type_data.fee_type if fee_type_data and fee_type_data.fee_type else "",
                    location_id=location_id,
                    destination_id=destination.destination_id,
                    terminal_id=terminal_id_for_order,
                    fee_type_id=fee_type_id,
                    user_uuid=self.user_uuid,
                    location_name=location.name,
                    location_city=location.city,
                    location_state=location.state,
                    location_postal_code=location.postal_code,
                    destination_name=destination.destination_name,
                    terminal_name=terminal_name_for_order,
                    fee_type_name=fee_type_data.fee_type if fee_type_data and fee_type_data.fee_type else "",
                ),
                flush=True,
            )

            items = self.build_invoice_items_from_order_data(
                order=order,
                default_calculator=default_calculator,
                cheapest_terminal=cheapest_terminal,
                transportation_city=transportation_city,
                ocean_city=ocean_city,
            )

            await order_service.create_invoice_items_batch(order.id, items)
            await db.commit()

            return order

    @classmethod
    def build_invoice_items_from_order_data(
        cls,
        *,
        order,
        default_calculator: calculator_pb2.DefaultCalculator,
        cheapest_terminal,
        transportation_city,
        ocean_city,
    ) -> list[InvoiceItemCreate]:
        items = [
            InvoiceItemCreate(
                name=f"{order.vehicle_name.upper()} ({order.vin})",
                amount=order.vehicle_value,
                order_id=order.id,
            ),
            InvoiceItemCreate(
                name="Broker Fee",
                amount=default_calculator.broker_fee,
                order_id=order.id,
            ),
        ]

        items.extend(
            InvoiceItemCreate(name=fee.name, amount=fee.price, order_id=order.id)
            for fee in default_calculator.additional.fees
            if fee.price
        )

        if cheapest_terminal:
            items.append(
                InvoiceItemCreate(
                    name=f"Transportation ({order.terminal_name})",
                    amount=transportation_city.price if transportation_city else 0,
                    order_id=order.id,
                )
            )
            items.append(
                InvoiceItemCreate(
                    name=f"Ocean Shipping ({order.terminal_name})",
                    amount=ocean_city.price if ocean_city else 0,
                    order_id=order.id,
                )
            )

        return items


if __name__ == "__main__":
    lot_id = 91467725
    auction = AuctionEnum.COPART
    user_uuid = 'acd4532b-014a-434f-b946-154a95e763b5'
    bid_amount = 1000
    generator = GenerateFromLot(lot_id=lot_id, auction=auction, user_uuid=user_uuid, bid_amount=100)

    async def main():
        await generator.generate()

    asyncio.run(main())
