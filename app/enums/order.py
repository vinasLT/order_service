from enum import Enum


class OrderStatusEnum(str, Enum):
    WON = 'won'
    PORT_CHOSEN = 'port_chosen'
    INVOICE_ADDED = 'invoice_added'
    TRACKING_ADDED = 'tracking_added'
    VEHICLE_IN_CUSTOM_AGENCY = 'vehicle_in_custom_agency'
    CUSTOM_INVOICE_ADDED = 'custom_invoice_added'
    DELIVERED = 'delivered'


class InvoiceTypeEnum(str, Enum):
    DEFAULT = "default"
