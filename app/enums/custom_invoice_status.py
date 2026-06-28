from enum import Enum


class FileInvoiceStatus(str, Enum):
    PENDING = 'pending'
    AVAILABLE = 'available'