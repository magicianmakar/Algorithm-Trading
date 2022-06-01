import asyncio
import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

import ujson

import hummingbot.connector.exchange.latoken.latoken_constants as CONSTANTS
import hummingbot.connector.exchange.latoken.latoken_web_utils as web_utils
from hummingbot.connector.constants import s_decimal_NaN
from hummingbot.connector.exchange.latoken.latoken_api_order_book_data_source import LatokenAPIOrderBookDataSource
from hummingbot.connector.exchange.latoken.latoken_api_user_stream_data_source import LatokenAPIUserStreamDataSource
from hummingbot.connector.exchange.latoken.latoken_auth import LatokenAuth
from hummingbot.connector.exchange.latoken.latoken_utils import (
    LatokenCommissionType,
    LatokenFeeSchema,
    LatokenTakeType,
    is_exchange_information_valid,
)
from hummingbot.connector.exchange_py_base import ExchangePyBase
from hummingbot.connector.trading_rule import TradingRule
from hummingbot.connector.utils import combine_to_hb_trading_pair
from hummingbot.core.data_type.in_flight_order import InFlightOrder, OrderUpdate, TradeUpdate
from hummingbot.core.data_type.order_book_tracker_data_source import OrderBookTrackerDataSource
from hummingbot.core.data_type.trade_fee import (
    AddedToCostTradeFee,
    DeductedFromReturnsTradeFee,
    TokenAmount,
    TradeFeeBase,
)
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.core.event.events import OrderType, TradeType
from hummingbot.core.network_iterator import NetworkStatus
from hummingbot.core.utils.async_utils import safe_gather
from hummingbot.core.utils.estimate_fee import build_trade_fee
from hummingbot.core.web_assistant.connections.data_types import RESTMethod
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory


class LatokenExchange(ExchangePyBase):

    web_utils = web_utils

    def __init__(self,
                 latoken_api_key: str,
                 latoken_api_secret: str,
                 trading_pairs: Optional[List[str]] = None,
                 trading_required: bool = True,
                 domain: str = CONSTANTS.DEFAULT_DOMAIN
                 ):

        self._domain = domain  # it is required to have this placed before calling super (why not as params to ctor?)
        self._api_key = latoken_api_key
        self._secret_key = latoken_api_secret
        self._trading_required = trading_required
        self._trading_pairs = trading_pairs
        super().__init__()

    @staticmethod
    def latoken_order_type(order_type: OrderType) -> str:
        return order_type.name.upper()

    @staticmethod
    def to_hb_order_type(latoken_type: str) -> OrderType:
        return OrderType[latoken_type]

    @property
    def authenticator(self):
        return LatokenAuth(
            api_key=self._api_key,
            secret_key=self._secret_key,
            time_provider=self._time_synchronizer)

    @property
    def rate_limits_rules(self):
        return CONSTANTS.RATE_LIMITS

    @property
    def domain(self):
        return self._domain

    @property
    def name(self) -> str:
        return "latoken" if self._domain == CONSTANTS.DEFAULT_DOMAIN else f"latoken_{self._domain}"

    @property
    def client_order_id_max_length(self):
        return CONSTANTS.MAX_ORDER_ID_LEN

    @property
    def client_order_id_prefix(self):
        return CONSTANTS.HBOT_ORDER_ID_PREFIX

    @property
    def trading_rules_request_path(self):  # not applicable because we need to request multiple REST endpoints
        raise NotImplementedError

    @property
    def check_network_request_path(self):
        return CONSTANTS.PING_PATH_URL

    def supported_order_types(self):
        return [OrderType.LIMIT]

    async def _place_cancel(self, order_id: str, tracked_order: InFlightOrder):
        exchange_order_id = await tracked_order.get_exchange_order_id()
        api_json = {"id": exchange_order_id}
        cancel_result = await self._api_post(
            path_url=CONSTANTS.ORDER_CANCEL_PATH_URL,
            data=api_json,
            is_auth_required=True)

        order_cancel_status = cancel_result.get("status")

        if order_cancel_status == "SUCCESS":
            return True
        else:  # order_cancel_status == "FAILURE":
            raise ValueError(f"Cancel order failed, no SUCCESS message {order_cancel_status}")

    async def _place_order(self,
                           order_id: str,
                           trading_pair: str,
                           amount: Decimal,
                           trade_type: TradeType,
                           order_type: OrderType,
                           price: Decimal) -> Tuple[str, float]:
        """
        Creates a an order in the exchange using the parameters to configure it
        :param trade_type: the side of the order (BUY of SELL)
        :param order_id: the id that should be assigned to the order (the client id)
        :param trading_pair: the token pair to operate with
        :param amount: the order amount
        :param order_type: the type of order to create (MARKET, LIMIT, LIMIT_MAKER)
        :param price: the order price
        """
        symbol = await self._orderbook_ds.exchange_symbol_associated_to_pair(
            trading_pair=trading_pair,
            domain=self._domain,
            api_factory=self._web_assistants_factory,
            throttler=self._throttler,
            time_synchronizer=self._time_synchronizer)

        quantized_price = self.quantize_order_price(trading_pair, price)
        quantize_amount_price = Decimal("0") if quantized_price.is_nan() else quantized_price
        quantized_amount = self.quantize_order_amount(trading_pair=trading_pair, amount=amount,
                                                      price=quantize_amount_price)
        price_str = f"{quantized_price:f}"
        amount_str = f"{quantized_amount:f}"
        type_str = self.latoken_order_type(order_type)
        side_str = CONSTANTS.SIDE_BUY if trade_type is TradeType.BUY else CONSTANTS.SIDE_SELL

        if type_str == OrderType.LIMIT_MAKER.name:
            self.logger().info('_create_order LIMIT_MAKER order not supported by Latoken, using LIMIT instead')

        base, quote = symbol.split('/')
        api_params = {
            'baseCurrency': base,
            'quoteCurrency': quote,
            "side": side_str,
            "clientOrderId": order_id,
            "quantity": amount_str,
            "type": OrderType.LIMIT.name,
            "price": price_str,
            "timestamp": int(datetime.datetime.now().timestamp() * 1000),
            'condition': CONSTANTS.TIME_IN_FORCE_GTC
        }

        order_result = await self._api_post(
            path_url=CONSTANTS.ORDER_PLACE_PATH_URL,
            data=api_params,
            is_auth_required=True)

        if order_result["status"] == "SUCCESS":
            exchange_order_id = str(order_result["id"])
            return exchange_order_id, datetime.datetime.now().timestamp()
        else:
            raise ValueError(f"Place order failed, no SUCCESS message {order_result}")

    def _get_fee(self,
                 base_currency: str,
                 quote_currency: str,
                 order_type: OrderType,
                 order_side: TradeType,
                 amount: Decimal,
                 price: Decimal = s_decimal_NaN,
                 is_maker: Optional[bool] = None) -> TradeFeeBase:
        """
        Calculates the estimated fee an order would pay based on the connector configuration
        :param base_currency: the order base currency
        :param quote_currency: the order quote currency
        :param order_type: the type of order (MARKET, LIMIT, LIMIT_MAKER)
        :param order_side: if the order is for buying or selling
        :param amount: the order amount
        :param price: the order price
        :param is_maker: if we take into account maker fee (True) or taker fee (None, False)
        :return: the estimated fee for the order
        """
        trading_pair = combine_to_hb_trading_pair(base=base_currency, quote=quote_currency)
        fee_schema = self._trading_fees.get(trading_pair, None)
        if fee_schema is None:
            self.logger().warning(f"For trading pair = {trading_pair} there is no fee schema loaded, using presets!")
            fee = build_trade_fee(
                self.name,
                is_maker,
                base_currency=base_currency,
                quote_currency=quote_currency,
                order_type=order_type,
                order_side=order_side,
                amount=amount,
                price=price)
        else:
            if fee_schema.type == LatokenTakeType.PROPORTION or fee_schema.take == LatokenCommissionType.PERCENT:
                pass  # currently not implemented but is nice to have in next release(s)
            percent = fee_schema.maker_fee if order_type is OrderType.LIMIT_MAKER or (
                is_maker is not None and is_maker) else fee_schema.taker_fee
            fee = AddedToCostTradeFee(
                percent=percent) if order_side == TradeType.BUY else DeductedFromReturnsTradeFee(percent=percent)

        return fee

    async def check_network(self) -> NetworkStatus:
        """
        Checks connectivity with the exchange using the API
        """
        try:
            await self._api_get(path_url=self.check_network_request_path, return_err=False)
        except asyncio.CancelledError:
            raise
        except Exception:
            return NetworkStatus.NOT_CONNECTED
        return NetworkStatus.CONNECTED

    async def _update_trading_rules(self):
        ticker_list, currency_list, pair_list = await safe_gather(
            self._api_get(path_url=CONSTANTS.TICKER_PATH_URL),
            self._api_get(path_url=CONSTANTS.CURRENCY_PATH_URL),
            self._api_get(path_url=CONSTANTS.PAIR_PATH_URL),
            return_exceptions=True)

        pairs = web_utils.create_full_mapping(ticker_list, currency_list, pair_list)
        trading_rules_list = await self._format_trading_rules(pairs)

        self._trading_rules.clear()
        for trading_rule in trading_rules_list:
            self._trading_rules[trading_rule.trading_pair] = trading_rule

    async def _api_request(self,
                           path_url: str,
                           method: RESTMethod,
                           params: Optional[Dict[str, Any]] = None,
                           data: Optional[Dict[str, Any]] = None,
                           is_auth_required: bool = False,
                           limit_id: Optional[str] = None,
                           return_err=True) -> Dict[str, Any]:
        return await web_utils.api_request(
            path=path_url,
            api_factory=self._web_assistants_factory,
            throttler=self._throttler,
            time_synchronizer=self._time_synchronizer,
            domain=self._domain,
            params=params,
            data=data,
            method=method,
            is_auth_required=is_auth_required,
            limit_id=limit_id,
            return_err=return_err
        )

    async def _update_trading_fees(self):
        fee_requests = [self._api_get(
            path_url=f"{CONSTANTS.FEES_PATH_URL}/{trading_pair.replace('-', '/')}",
            is_auth_required=True, limit_id=CONSTANTS.FEES_PATH_URL) for trading_pair in self._trading_pairs]
        responses = zip(self._trading_pairs, await safe_gather(*fee_requests, return_exceptions=True))
        for trading_pair, response in responses:
            self._trading_fees[trading_pair] = None if isinstance(response, Exception) else LatokenFeeSchema(response)

    async def _user_stream_event_listener(self):
        """
        This functions runs in background continuously processing the events received from the exchange by the user
        stream data source. It keeps reading events from the queue until the task is interrupted.
        The events received are balance updates, order updates and trade events.
        """
        async for event_message in self._iter_user_event_queue():
            try:
                cmd = event_message.get('cmd', None)
                if cmd and cmd == 'MESSAGE':
                    subscription_id = int(event_message['headers']['subscription'].split('_')[0])
                    payload = ujson.loads(event_message["body"])["payload"]

                    if subscription_id == CONSTANTS.SUBSCRIPTION_ID_ACCOUNT:
                        await self._process_account_balance_update(balances=payload)
                    elif subscription_id == CONSTANTS.SUBSCRIPTION_ID_ORDERS:
                        for update in payload:  # self.logger().error(str(orders))
                            await self._process_order_update(update)
                    elif subscription_id == CONSTANTS.SUBSCRIPTION_ID_TRADE_UPDATE:
                        for update in payload:
                            await self._process_trade_update(update)
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger().error("Unexpected error in user stream listener loop.", exc_info=True)
                await asyncio.sleep(5.0)

    async def _format_trading_rules(self, pairs_list: List[Any]) -> List[TradingRule]:
        """
        Example: https://api.latoken.com/doc/v2/#tag/Pair
        [
            {
            "id": "263d5e99-1413-47e4-9215-ce4f5dec3556",
            "status": "PAIR_STATUS_ACTIVE",
            "baseCurrency": "6ae140a9-8e75-4413-b157-8dd95c711b23",
            "quoteCurrency": "23fa548b-f887-4f48-9b9b-7dd2c7de5ed0",
            "priceTick": "0.010000000",
            "priceDecimals": 2,
            "quantityTick": "0.010000000",
            "quantityDecimals": 2,
            "costDisplayDecimals": 3,
            "created": 1571333313871,
            "minOrderQuantity": "0",
            "maxOrderCostUsd": "999999999999999999",
            "minOrderCostUsd": "0",
            "externalSymbol": ""
            }
        ]
        """
        trading_rules = []
        for rule in filter(is_exchange_information_valid, pairs_list):
            try:
                symbol = f"{rule['id']['baseCurrency']}/{rule['id']['quoteCurrency']}"
                trading_pair = await self._orderbook_ds.trading_pair_associated_to_exchange_symbol(
                    symbol=symbol, domain=self._domain, api_factory=self._web_assistants_factory, throttler=self._throttler)

                min_order_size = Decimal(rule["minOrderQuantity"])
                price_tick = Decimal(rule["priceTick"])
                quantity_tick = Decimal(rule["quantityTick"])
                min_order_value = Decimal(rule["minOrderCostUsd"])
                min_order_quantity = Decimal(rule["minOrderQuantity"])

                trading_rule = TradingRule(
                    trading_pair,
                    min_order_size=max(min_order_size, quantity_tick),
                    min_price_increment=price_tick,
                    min_base_amount_increment=quantity_tick,
                    min_quote_amount_increment=price_tick,
                    min_notional_size=min_order_quantity,
                    min_order_value=min_order_value,
                    # max_price_significant_digits=len(rule["maxOrderCostUsd"])
                    # supports_market_orders = False,
                )

                trading_rules.append(trading_rule)

            except Exception:
                self.logger().exception(f"Error parsing the trading pair rule {rule}. Skipping.")
        return trading_rules

    async def _update_order_status(self):
        # This is intended to be a backup measure to close straggler orders, in case Latoken's user stream events
        # are not working.
        # The minimum poll interval for order status is 10 seconds.
        last_tick = self._last_poll_timestamp / CONSTANTS.UPDATE_ORDER_STATUS_MIN_INTERVAL
        current_tick = self.current_timestamp / CONSTANTS.UPDATE_ORDER_STATUS_MIN_INTERVAL

        tracked_orders: List[InFlightOrder] = list(self.in_flight_orders.values())

        if current_tick <= last_tick or len(tracked_orders) == 0:
            return
        # if current_tick > last_tick and len(tracked_orders) > 0:
        # not sure if the exchange order id is always up-to-date on the moment this function is called (?)

        reviewed_orders = []
        tasks = []

        for tracked_order in tracked_orders:
            try:
                exchange_order_id = await tracked_order.get_exchange_order_id()
            except asyncio.TimeoutError:
                self.logger().debug(
                    f"Tracked order {tracked_order.client_order_id} does not have an exchange id. "
                    f"Attempting fetch in next polling interval."
                )
                await self._order_tracker.process_order_not_found(tracked_order.client_order_id)
                continue
            reviewed_orders.append(tracked_order)
            tasks.append(
                self._api_get(
                    path_url=f"{CONSTANTS.GET_ORDER_PATH_URL}/{exchange_order_id}",
                    is_auth_required=True,
                    return_err=False,
                    limit_id=CONSTANTS.GET_ORDER_PATH_URL))

        self.logger().debug(f"Polling for order status updates of {len(tasks)} orders.")
        results = await safe_gather(*tasks, return_exceptions=True)
        for order_update, tracked_order in zip(results, reviewed_orders):
            client_order_id = tracked_order.client_order_id

            # If the order has already been cancelled or has failed do nothing
            if client_order_id not in self.in_flight_orders:
                continue

            if isinstance(order_update, Exception):
                self.logger().network(
                    f"Error fetching status update for the order {client_order_id}: {order_update}.",
                    app_warning_msg=f"Failed to fetch status update for the order {client_order_id}."
                )
                # Wait until the order not found error have repeated a few times before actually treating
                # it as failed. See: https://github.com/CoinAlpha/hummingbot/issues/601
                await self._order_tracker.process_order_not_found(client_order_id)
            else:
                # Update order execution status
                status = order_update["status"]
                filled = Decimal(order_update["filled"])
                quantity = Decimal(order_update["quantity"])

                new_state = web_utils.get_order_status_rest(status=status, filled=filled, quantity=quantity)

                update = OrderUpdate(
                    client_order_id=client_order_id,
                    exchange_order_id=order_update["id"],
                    trading_pair=tracked_order.trading_pair,
                    update_timestamp=float(order_update["timestamp"]) * 1e-3,
                    new_state=new_state,
                )
                self._order_tracker.process_order_update(update)

    async def _update_balances(self):
        try:
            params = {'zeros': 'false'}  # if not testing this can be set to the default of false
            balances = await self._api_get(path_url=CONSTANTS.ACCOUNTS_PATH_URL, is_auth_required=True, params=params)
            remote_asset_names = await self._process_account_balance_update(balances)
            self._process_full_account_balances_refresh(remote_asset_names, balances)
        except IOError:
            self.logger().exception("Error getting account balances from server")

    def _create_web_assistants_factory(self) -> WebAssistantsFactory:
        return web_utils.build_api_factory(
            throttler=self._throttler,
            time_synchronizer=self._time_synchronizer,
            domain=self.domain,
            auth=self._auth)

    def _create_order_book_data_source(self) -> OrderBookTrackerDataSource:
        return LatokenAPIOrderBookDataSource(
            trading_pairs=self._trading_pairs,
            domain=self.domain,
            api_factory=self._web_assistants_factory,
            throttler=self._throttler,
            time_synchronizer=self._time_synchronizer,
        )

    def _create_user_stream_data_source(self) -> UserStreamTrackerDataSource:
        return LatokenAPIUserStreamDataSource(
            auth=self._auth,
            trading_pairs=self._trading_pairs,
            domain=self.domain,
            api_factory=self._web_assistants_factory,
            throttler=self._throttler,
            time_synchronizer=self._time_synchronizer,
        )

    async def _process_account_balance_update(self, balances):
        remote_asset_names = set()

        balance_to_gather = [
            self._api_get(path_url=f"{CONSTANTS.CURRENCY_PATH_URL}/{balance['currency']}", limit_id=CONSTANTS.CURRENCY_PATH_URL) for balance in balances]

        # maybe request every currency if len(account_balance) > 5
        currency_lists = await safe_gather(*balance_to_gather, return_exceptions=True)

        currencies = {currency["id"]: currency["tag"] for currency in currency_lists if
                      isinstance(currency, dict) and currency["status"] != 'FAILURE'}

        for balance in balances:
            if balance['status'] == "FAILURE" and balance['error'] == 'NOT_FOUND':
                self.logger().error(f"Could not resolve currency details for balance={balance}")
                continue
            asset_name = currencies.get(balance["currency"], None)
            if asset_name is None or balance["type"] != "ACCOUNT_TYPE_SPOT":
                if asset_name is None:
                    self.logger().error(f"Could not resolve currency details for balance={balance}")
                continue
            free_balance = Decimal(balance["available"])
            total_balance = free_balance + Decimal(balance["blocked"])
            self._account_available_balances[asset_name] = free_balance
            self._account_balances[asset_name] = total_balance
            remote_asset_names.add(asset_name)

        return remote_asset_names

    def _process_full_account_balances_refresh(self, remote_asset_names, balances):
        """ use this for rest call and not ws because ws does not send entire account balance list"""
        local_asset_names = set(self._account_balances.keys())
        if not balances:
            self.logger().warning("Fund your latoken account, no balances in your account!")
        has_spot_balances = any(filter(lambda b: b["type"] == "ACCOUNT_TYPE_SPOT", balances))
        if balances and not has_spot_balances:
            self.logger().warning(
                "No latoken SPOT balance! Account has balances but no SPOT balance! Transfer to Latoken SPOT account!")
        # clean-up balances that are not present anymore
        asset_names_to_remove = local_asset_names.difference(remote_asset_names)
        for asset_name in asset_names_to_remove:
            del self._account_available_balances[asset_name]
            del self._account_balances[asset_name]

    async def _process_trade_update(self, trade):
        symbol = f"{trade['baseCurrency']}/{trade['quoteCurrency']}"
        trading_pair = await self._orderbook_ds.trading_pair_associated_to_exchange_symbol(
            symbol=symbol, domain=self._domain, api_factory=self._web_assistants_factory, throttler=self._throttler)

        base_currency, quote_currency = trading_pair.split('-')
        trade_type = TradeType.BUY if trade["makerBuyer"] else TradeType.SELL
        timestamp = float(trade["timestamp"]) * 1e-3
        quantity = Decimal(trade["quantity"])
        price = Decimal(trade["price"])
        trade_id = trade["id"]
        exchange_order_id = trade["order"]
        tracked_order = self._order_tracker.fetch_order(exchange_order_id=exchange_order_id)
        client_order_id = tracked_order.client_order_id if tracked_order else self._exchange_order_ids.get(
            exchange_order_id, None)

        absolute_fee = Decimal(trade["fee"])
        fee = TradeFeeBase.new_spot_fee(
            fee_schema=self.trade_fee_schema(), trade_type=trade_type,
            percent_token=quote_currency,
            flat_fees=[TokenAmount(amount=absolute_fee, token=quote_currency)])

        trade_update = TradeUpdate(
            trade_id=trade_id,
            exchange_order_id=exchange_order_id,
            client_order_id=client_order_id,
            trading_pair=trading_pair,  # or tracked_order.trading_pair
            fill_timestamp=timestamp,
            fill_price=price,
            fill_base_amount=quantity,
            fill_quote_amount=Decimal(trade["cost"]),
            fee=fee,
        )

        self._order_tracker.process_trade_update(trade_update)

    async def _process_order_update(self, order):
        symbol = f"{order['baseCurrency']}/{order['quoteCurrency']}"
        trading_pair = await self._orderbook_ds.trading_pair_associated_to_exchange_symbol(
            symbol=symbol, domain=self._domain, api_factory=self._web_assistants_factory, throttler=self._throttler)
        client_order_id = order['clientOrderId']

        change_type = order['changeType']
        status = order['status']
        quantity = Decimal(order["quantity"])
        filled = Decimal(order['filled'])
        delta_filled = Decimal(order['deltaFilled'])

        state = web_utils.get_order_status_ws(change_type, status, quantity, filled, delta_filled)
        if state is None:
            return

        timestamp = float(order["timestamp"]) * 1e-3

        order_update = OrderUpdate(
            trading_pair=trading_pair,
            update_timestamp=timestamp,
            new_state=state,
            client_order_id=client_order_id,
        )

        self._order_tracker.process_order_update(order_update=order_update)
