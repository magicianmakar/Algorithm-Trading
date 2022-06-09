from decimal import Decimal
from typing import Optional, Tuple

from hummingbot.connector.constants import s_decimal_NaN
from hummingbot.connector.exchange.clob import clob_constants as constant
from hummingbot.connector.exchange_py_base import ExchangePyBase
from hummingbot.core.data_type.common import OrderType, TradeType
from hummingbot.core.data_type.order_book_tracker_data_source import OrderBookTrackerDataSource
from hummingbot.core.data_type.trade_fee import DeductedFromReturnsTradeFee, TradeFeeBase
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory


class CLOBExchange(ExchangePyBase):
    @property
    def domain(self):
        return self._domain

    def name(self):
        if self._domain == "com":
            return "clob"
        else:
            return f"clob_{self._domain}"

    @property
    def authenticator(self):
        pass

    @property
    def rate_limits_rules(self):
        return constant.RATE_LIMITS

    @property
    def client_order_id_max_length(self):
        return constant.MAX_CLIENT_ORDER_ID_LENGTH

    @property
    def client_order_id_prefix(self):
        return constant.CLIENT_ORDER_ID_PREFIX

    @property
    def trading_rules_request_path(self):
        return constant.TRADING_RULES_REQUEST_PATH

    @property
    def check_network_request_path(self):
        return constant.CHECK_NETWORK_REQUEST_PATH

    def supported_order_types(self):
        # TODO Include IoC and post only?!!!
        return [OrderType.LIMIT, OrderType.LIMIT_MAKER]

    async def _place_order(
        self,
        order_id: str,
        trading_pair: str,
        amount: Decimal,
        trade_type: TradeType,
        order_type: OrderType,
        price: Decimal
    ) -> Tuple[str, float]:
        if trade_type not in [TradeType.BUY, TradeType.SELL]:
            raise ValueError(f'Unrecognized order side "{trade_type}".')

        if order_type not in [OrderType.LIMIT]:
            raise ValueError(f'Unrecognized order type "{order_type}".')

        parameters = {
            "id": order_id,
            "marketName": trading_pair,
            "ownerAddress": "",  # TODO fix!!!
            "payerAddress": "",  # TODO fix!!!
            "side": trade_type.name,
            "price": price,
            "amount": amount,
            "type": order_type,
        }

        created_order = await self._api_post(
            path_url=constant.ORDER_PATH_URL,
            data=parameters,
            is_auth_required=True
        )

        client_order_id = str(created_order["id"])
        transaction_time = 0.0  # TODO fix!!!

        return client_order_id, transaction_time

    async def _place_cancel(
        self,
        order_id: str,
        trading_pair: str
    ) -> bool:
        parameters = {
            "id": id,
            "marketName": trading_pair,
            "ownerAddress": "",  # TODO fix!!!
        }

        canceled_order = await self._api_delete(
            path_url=constant.ORDER_PATH_URL,
            params=parameters,
            is_auth_required=True
        )

        if canceled_order.get("status") == "CANCELED":
            return True

        return False

    def _get_fee(
        self,
        base_currency: str,
        quote_currency: str,
        order_type: OrderType,
        order_side: TradeType,
        amount: Decimal,
        price: Decimal = s_decimal_NaN,
        is_maker: Optional[bool] = None
    ) -> TradeFeeBase:  # TODO check this return type, it is different from abstract!!!
        is_maker = order_type is OrderType.LIMIT_MAKER

        return DeductedFromReturnsTradeFee(percent=self.estimate_fee_pct(is_maker))

    async def _update_trading_fees(self):
        pass

    def _user_stream_event_listener(self):
        pass

    def _format_trading_rules(self):
        pass

    def _update_order_status(self):
        pass

    def _update_balances(self):
        pass

    def _create_web_assistants_factory(self) -> WebAssistantsFactory:
        pass

    def _create_order_book_data_source(self) -> OrderBookTrackerDataSource:
        pass

    def _create_user_stream_data_source(self) -> UserStreamTrackerDataSource:
        pass

    def c_stop_tracking_order(self, order_id):
        pass
