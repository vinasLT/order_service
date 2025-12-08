from enum import Enum


class RoutingKeys(str, Enum):
    FILES_UPLOADED = 'files.uploaded'
    BID_WON = 'bid.you_won_bid'