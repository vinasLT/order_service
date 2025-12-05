from fastapi import APIRouter

from app.routers.private.v1.status import (
    custom_invoice_added,
    delivered,
    make_invoice_visible,
    tracking_link,
    vehicle_in_custom_agency,
)

status_router = APIRouter()
status_router.include_router(make_invoice_visible.make_invoice_visible_router)
status_router.include_router(tracking_link.tracking_link_router)
status_router.include_router(vehicle_in_custom_agency.vehicle_in_custom_agency_router)
status_router.include_router(custom_invoice_added.custom_invoice_added_router)
status_router.include_router(delivered.delivered_router)

__all__ = [
    "status_router",
]
