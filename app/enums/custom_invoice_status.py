from enum import Enum


class CustomInvoiceStatus(str, Enum):
    PENDING = 'pending'
    AVAILABLE = 'available'