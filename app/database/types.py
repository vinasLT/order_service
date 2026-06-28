from sqlalchemy import Enum

from app.enums.custom_invoice_status import FileInvoiceStatus

# Shared PostgreSQL enum type for custom_invoice and auction_invoice status columns.
file_invoice_status_enum = Enum(FileInvoiceStatus, name='custominvoicestatus')
