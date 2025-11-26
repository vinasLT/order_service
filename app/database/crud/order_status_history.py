from sqlalchemy.ext.asyncio import AsyncSession

from app.database.crud.base import BaseService
from app.database.models.order import OrderStatusHistory
from app.database.schemas.order_status_history import OrderStatusHistoryCreate, OrderStatusHistoryUpdate


class OrderStatusHistoryService(BaseService[OrderStatusHistory, OrderStatusHistoryCreate, OrderStatusHistoryUpdate]):
    def __init__(self, session: AsyncSession):
        super().__init__(OrderStatusHistory, session)
