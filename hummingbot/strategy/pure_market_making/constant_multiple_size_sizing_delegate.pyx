from hummingbot.core.data_type.limit_order import LimitOrder
from hummingbot.market.market_base cimport MarketBase
from hummingbot.market.market_base import MarketBase

from .data_types import SizingProposal
from .pure_market_making_v2 cimport PureMarketMakingStrategyV2


cdef class ConstantSizeSizingDelegate(OrderSizingDelegate):
    def __init__(self, order_size: float, number_of_orders:int):
        super().__init__()
        self._order_size = order_size
        self._number_of_orders = number_of_orders

    @property
    def order_size(self) -> float:
        return self._order_size

    @property
    def number_of_orders(self) -> int:
        return self._number_of_orders

    cdef object c_get_order_size_proposal(self,
                                          PureMarketMakingStrategyV2 strategy,
                                          object market_info,
                                          list active_orders,
                                          object pricing_proposal):
        cdef:
            MarketBase market = market_info.market
            double base_asset_balance = market.c_get_balance(market_info.base_currency)
            double quote_asset_balance = market.c_get_balance(market_info.quote_currency)
            double required_quote_asset_balance = 0
            double per_order_size = self._order_size / self._number_of_orders
            bint has_active_bid = False
            bint has_active_ask = False

        for active_order in active_orders:
            if active_order.is_buy:
                has_active_bid = True
            else:
                has_active_ask = True

        for idx in range(self._number_of_orders):
            required_quote_asset_balance += ( per_order_size * pricing_proposal.buy_order_price[idx] )


        return SizingProposal(
            ([per_order_size] * self.number_of_orders
             if quote_asset_balance > required_quote_asset_balance and not has_active_bid
             else 0.0),
            ([per_order_size] * self.number_of_orders
             if base_asset_balance > self.order_size and not has_active_ask else
             0.0)
        )