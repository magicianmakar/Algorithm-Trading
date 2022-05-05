from decimal import Decimal
from typing import Optional, Dict, Any, List

from hummingbot.connector.exchange.bitmex.bitmex_order_status import BitmexOrderStatus
from hummingbot.connector.in_flight_order_base import InFlightOrderBase
from hummingbot.core.event.events import (TradeType, OrderType, MarketEvent)


class BitmexInFlightOrder(InFlightOrderBase):
    def __init__(self,
                 client_order_id: str,
                 exchange_order_id: Optional[str],
                 trading_pair: str,
                 order_type: OrderType,
                 trade_type: TradeType,
                 price: Decimal,
                 amount: Decimal,
                 created_at: float,
                 initial_state: str = "New"):
        super().__init__(
            client_order_id,
            exchange_order_id,
            trading_pair,
            order_type,
            trade_type,
            price,
            amount,
            created_at,
            initial_state
        )
        self.created_at = created_at
        self.state = BitmexOrderStatus.New

    def __repr__(self) -> str:
        return f"super().__repr__()" \
               f"created_at='{str(self.created_at)}'')"

    def to_json(self) -> Dict[str, Any]:
        response = super().to_json()
        response["created_at"] = str(self.created_at)
        return response

    @property
    def is_done(self) -> bool:
        return self.state in [BitmexOrderStatus.Canceled, BitmexOrderStatus.Filled, BitmexOrderStatus.FAILURE]

    @property
    def is_failure(self) -> bool:
        return self.state is BitmexOrderStatus.FAILURE or self.is_cancelled

    @property
    def is_cancelled(self) -> bool:
        return self.state is BitmexOrderStatus.Canceled and self.executed_amount_base < self.amount

    def set_status(self, status: str):
        self.last_state = status
        self.state = BitmexOrderStatus[status]

    @property
    def order_type_description(self) -> str:
        order_type = "market" if self.order_type is OrderType.MARKET else "limit"
        side = "buy" if self.trade_type is TradeType.BUY else "sell"
        return f"{order_type} {side}"

    @classmethod
    def from_json(cls, data: Dict[str, Any]) -> InFlightOrderBase:
        retval: BitmexInFlightOrder = BitmexInFlightOrder(
            data["client_order_id"],
            data["exchange_order_id"],
            data["trading_pair"],
            getattr(OrderType, data["order_type"]),
            getattr(TradeType, data["trade_type"]),
            Decimal(data["price"]),
            Decimal(data["amount"]),
            float(data["created_at"] if "created_at" in data else 0),
            data["last_state"],
        )
        retval.executed_amount_base = Decimal(data.get("executed_amount_base", '0'))
        retval.executed_amount_quote = Decimal(data.get("executed_amount_quote", '0'))
        last_state = int(data["last_state"])
        retval.state = BitmexOrderStatus(last_state)
        return retval

    def update(self, data: Dict[str, Any]) -> List[Any]:
        events: List[Any] = []

        incoming_status = data.get("ordStatus")
        if incoming_status is not None:
            new_status: BitmexOrderStatus = BitmexOrderStatus[data["ordStatus"]]
        else:
            if self.status < BitmexOrderStatus.Cancelled:
                # no status is sent over websocket fills
                new_status: BitmexOrderStatus = BitmexOrderStatus.PartiallyFilled
            else:
                new_status = self.status
        old_executed_base: Decimal = self.executed_amount_base
        old_executed_quote: Decimal = self.executed_amount_quote
        if new_status == BitmexOrderStatus.Canceled:
            overall_executed_base = self.executed_amount_base
            overall_remaining_size = self.amount - overall_executed_base
            overall_executed_quote = self.executed_amount_quote
        else:
            if "amount_remaining" in data:
                overall_remaining_size: Decimal = data["amount_remaining"]
                overall_executed_base: Decimal = self.amount - overall_remaining_size
            else:
                overall_remaining_quote: Decimal = Decimal(str(data["quote_amount_remaining"]))
                overall_remaining_size: Decimal = overall_remaining_quote / Decimal(str(data["price"]))
                overall_executed_base: Decimal = self.amount - overall_remaining_size

            if data.get("avgPx") is not None:
                overall_executed_quote: Decimal = overall_executed_base * Decimal(str(data["avgPx"]))
            else:
                overall_executed_quote: Decimal = Decimal("0")

        diff_base: Decimal = overall_executed_base - old_executed_base
        diff_quote: Decimal = overall_executed_quote - old_executed_quote

        if diff_base > 0:
            diff_price: Decimal = diff_quote / diff_base
            events.append((MarketEvent.OrderFilled, diff_base, diff_price, None))
            self.executed_amount_base = overall_executed_base
            self.executed_amount_quote = overall_executed_quote

        if not self.is_done and new_status in [BitmexOrderStatus.Canceled, BitmexOrderStatus.Filled]:
            if overall_remaining_size > 0:
                events.append((MarketEvent.OrderCancelled, None, None, None))
            elif self.trade_type is TradeType.BUY:
                events.append((MarketEvent.BuyOrderCompleted, overall_executed_base, overall_executed_quote, None))
            else:
                events.append((MarketEvent.SellOrderCompleted, overall_executed_base, overall_executed_quote, None))

        self.state = new_status
        self.last_state = new_status.name

        return events
