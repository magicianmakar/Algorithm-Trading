#!/usr/bin/env python
from typing import (
    NamedTuple,
    List
)
from decimal import Decimal
from hummingbot.core.event.events import OrderType

ORDER_PROPOSAL_ACTION_CREATE_ORDERS = 1
ORDER_PROPOSAL_ACTION_CANCEL_ORDERS = 1 << 1


class OrdersProposal(NamedTuple):
    actions: int
    buy_order_type: OrderType
    buy_order_prices: List[Decimal]
    buy_order_sizes: List[Decimal]
    sell_order_type: OrderType
    sell_order_prices: List[Decimal]
    sell_order_sizes: List[Decimal]
    cancel_order_ids: List[str]


class PricingProposal(NamedTuple):
    buy_order_prices: List[Decimal]
    sell_order_prices: List[Decimal]


class SizingProposal(NamedTuple):
    buy_order_sizes: List[Decimal]
    sell_order_sizes: List[Decimal]


class InventorySkewBidAskRatios(NamedTuple):
    bid_ratio: float
    ask_ratio: float


class PriceSize(NamedTuple):
    price: Decimal
    size: Decimal


class Proposal(NamedTuple):
    buys: List[PriceSize]
    sells: List[PriceSize]
