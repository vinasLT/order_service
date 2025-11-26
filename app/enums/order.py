from enum import Enum


class OrderStatusEnum(str, Enum):
    PENDING_PAYMENT = "pending_payment"
    PAID = "paid"
    UNPAID = "unpaid"
    PICKED_UP = "picked_up"
    DELIVERED_TERMINAL = "delivered_terminal"
    NO_TITLE = "no_title"
    LOADED_INTO_CONTAINER = "loaded_into_container"


class InvoiceTypeEnum(str, Enum):

