import time

import aiohttp
import asyncio
import logging
import ujson

import hummingbot.connector.derivative.bybit_perpetual.bybit_perpetual_utils as bybit_utils
import hummingbot.connector.derivative.bybit_perpetual.bybit_perpetual_constants as CONSTANTS

from decimal import Decimal
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from hummingbot.connector.derivative.bybit_perpetual.bybit_perpetual_auth import BybitPerpetualAuth
from hummingbot.connector.derivative.bybit_perpetual.bybit_perpetual_api_order_book_data_source import \
    BybitPerpetualAPIOrderBookDataSource
from hummingbot.connector.exchange_base import ExchangeBase, CancellationResult

from hummingbot.connector.derivative.bybit_perpetual.bybit_perpetual_in_flight_order import BybitPerpetualInFlightOrder
from hummingbot.connector.derivative.bybit_perpetual.bybit_perpetual_order_book_tracker import \
    BybitPerpetualOrderBookTracker
from hummingbot.connector.perpetual_trading import PerpetualTrading
from hummingbot.connector.trading_rule import TradingRule

from hummingbot.core.data_type.order_book import OrderBook

from hummingbot.core.data_type.limit_order import LimitOrder
from hummingbot.core.event.events import (
    FundingInfo,
    MarketEvent,
    MarketOrderFailureEvent,
    OrderType,
    PositionAction,
    PositionMode,
    TradeType, TradeFee, OrderCancelledEvent, BuyOrderCreatedEvent, SellOrderCreatedEvent,
)
from hummingbot.core.utils.async_utils import safe_ensure_future, safe_gather
from hummingbot.logger import HummingbotLogger

s_decimal_NaN = Decimal("nan")
s_decimal_0 = Decimal(0)


class BybitPerpetualDerivative(ExchangeBase, PerpetualTrading):
    _logger = None

    _DEFAULT_TIME_IN_FORCE = "GoodTillCancel"
    UPDATE_TRADING_RULES_INTERVAL = 60

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._logger is None:
            cls._logger = logging.getLogger(__name__)
        return cls._logger

    def __init__(self,
                 bybit_perpetual_api_key: str = None,
                 bybit_perpetual_secret_key: str = None,
                 trading_pairs: Optional[List[str]] = None,
                 trading_required: bool = True,
                 domain: Optional[str] = None):

        ExchangeBase.__init__(self)
        PerpetualTrading.__init__(self)

        self._trading_pairs = trading_pairs
        self._trading_required = trading_required
        self._domain = domain
        self._shared_client = None

        self._auth: BybitPerpetualAuth = BybitPerpetualAuth(api_key=bybit_perpetual_api_key,
                                                            secret_key=bybit_perpetual_secret_key)
        self._order_book_tracker = BybitPerpetualOrderBookTracker(
            session=asyncio.get_event_loop().run_until_complete(self._aiohttp_client()),
            trading_pairs=trading_pairs,
            domain=domain)
        # self._user_stream_tracker = BybitPerpetualUserStreamTracker(self._auth, domain=domain)

        self._in_flight_orders = {}
        self._trading_rules = {}

        # Tasks
        self._funding_info_polling_task = None
        self._user_funding_fee_polling_task = None
        self._status_polling_task = None
        self._user_stream_tracker_task = None
        self._user_stream_event_listener_task = None
        self._trading_rules_polling_task = None

    @property
    def name(self) -> str:
        return CONSTANTS.EXCHANGE_NAME

    @property
    def trading_rules(self) -> Dict[str, TradingRule]:
        return self._trading_rules

    @property
    def in_flight_orders(self) -> Dict[str, BybitPerpetualInFlightOrder]:
        return self._in_flight_orders

    @property
    def status_dict(self) -> Dict[str, bool]:
        """
        A dictionary of statuses of various exchange's components. Used to determine if the connector is ready
        """
        return {
            "order_books_initialized": self._order_book_tracker.ready,
            "account_balance": not self._trading_required or len(self._account_balances) > 0,
            "trading_rule_initialized": len(self._trading_rules) > 0,
            # "user_stream_initialized":
            #     not self._trading_required or self._user_stream_tracker.data_source.last_recv_time > 0,
            "funding_info": len(self._funding_info) > 0
        }

    @property
    def ready(self) -> bool:
        """
        Determines if the connector is ready.
        :return True when all statuses pass, this might take 5-10 seconds for all the connector's components and
        services to be ready.
        """
        return all(self.status_dict.values())

    @property
    def order_books(self) -> Dict[str, OrderBook]:
        return self._order_book_tracker.order_books

    @property
    def limit_orders(self) -> List[LimitOrder]:
        return [
            in_flight_order.to_limit_order()
            for in_flight_order in self._in_flight_orders.values()
        ]

    @property
    def tracking_states(self) -> Dict[str, Any]:
        """
        :return: active in-flight order in JSON format. Used to save order entries into local sqlite database.
        """
        return {
            client_oid: order.to_json()
            for client_oid, order in self._in_flight_orders.items()
            if not order.is_done
        }

    def restore_tracking_states(self, saved_states: Dict[str, Any]):
        """
        Restore in-flight orders from the saved tracking states(from local db). This is such that the connector can pick
        up from where it left off before Hummingbot client was terminated.
        :param saved_states: The saved tracking_states.
        """
        self._in_flight_orders.update({
            client_oid: BybitPerpetualInFlightOrder.from_json(order_json)
            for client_oid, order_json in saved_states.items()
        })

    async def _aiohttp_client(self) -> aiohttp.ClientSession:
        """
        :returns Shared aiohttp Client session
        """
        if self._shared_client is None:
            self._shared_client = aiohttp.ClientSession()
        return self._shared_client

    def supported_position_modes(self) -> List[PositionMode]:
        return [PositionMode.ONEWAY, PositionMode.HEDGE]

    async def start_network(self):
        self._order_book_tracker.start()
        self._trading_rules_polling_task = safe_ensure_future(self._trading_rules_polling_loop())
        self._funding_info_polling_task = safe_ensure_future(self._funding_info_polling_loop())
        if self._trading_required:
            self._status_polling_task = safe_ensure_future(self._status_polling_loop())
            # self._user_stream_tracker_task = safe_ensure_future(self._user_stream_tracker.start())
            # self._user_stream_event_listener_task = safe_ensure_future(self._user_stream_event_listener())
            self._user_funding_fee_polling_task = safe_ensure_future(self._user_funding_fee_polling_loop())

    async def stop_network(self):
        self._order_book_tracker.stop()
        if self._status_polling_task is not None:
            self._status_polling_task.cancel()
            self._status_polling_task = None
        if self._trading_rules_polling_task is not None:
            self._trading_rules_polling_task.cancel()
            self._trading_rules_polling_task = None
        if self._user_stream_tracker_task is not None:
            self._user_stream_tracker_task.cancel()
            self._user_stream_tracker_task = None
        if self._user_stream_event_listener_task is not None:
            self._user_stream_event_listener_task.cancel()
            self._user_stream_event_listener_task = None
        if self._funding_info_polling_task is not None:
            self._funding_info_polling_task.cancel()
            self._funding_info_polling_task = None
        if self._user_funding_fee_polling_task is not None:
            self._user_funding_fee_polling_task.cancel()
            self._user_funding_fee_polling_task = None

    def supported_order_types(self) -> List[OrderType]:
        """
        :return a list of OrderType supported by this connector
        """
        return [OrderType.LIMIT, OrderType.MARKET]

    async def _trading_pair_symbol(self, trading_pair: str) -> str:
        return await self._order_book_tracker.trading_pair_symbol(trading_pair)

    async def _api_request(self,
                           method: str,
                           path_url: str,
                           params: Optional[Dict[str, Any]] = None,
                           body: Optional[Dict[str, Any]] = None,
                           is_auth_required: bool = False,
                           ):
        """
        Sends an aiohttp request and waits for a response.
        :param method: The HTTP method, e.g. get or post
        :param path_url: The path url or the API end point
        :param params: The query parameters of the API request
        :param body: The body parameters of the API request
        :param is_auth_required: Whether an authentication is required, when True the function will add encrypted
        signature to the request.
        :returns A response in json format.
        """
        url = bybit_utils.rest_api_url_for_endpoint(path_url, self._domain)
        client = await self._aiohttp_client()

        if method == "GET":
            if is_auth_required:
                params = self._auth.extend_params_with_authentication_info(params=params)
            response = await client.get(url=url,
                                        headers=self._auth.get_headers(),
                                        params=params,
                                        )
        elif method == "POST":
            if is_auth_required:
                params = self._auth.extend_params_with_authentication_info(params=body)
            response = await client.post(url=url,
                                         headers=self._auth.get_headers(),
                                         data=ujson.dumps(params)
                                         )
        else:
            raise NotImplementedError(f"{method} HTTP Method not implemented. ")

        response_status = response.status
        parsed_response: Dict[str, Any] = await response.json()

        if response_status != 200 or (
                isinstance(parsed_response, dict) and not parsed_response.get("result", True)):
            self.logger().error(f"Error fetching data from {url}. HTTP status is {response_status}. "
                                f"Message: {parsed_response} "
                                f"Params: {params} "
                                f"Data: {body}")
            raise Exception(f"Error fetching data from {url}. HTTP status is {response_status}. "
                            f"Message: {parsed_response} "
                            f"Params: {params} "
                            f"Data: {body}")

        return parsed_response

    def get_order_price_quantum(self, trading_pair: str, price: Decimal) -> Decimal:
        """
        Returns a price step, a minimum price increment for a given trading pair.
        :param trading_pair: trading pair for which the price quantum will be calculated
        :param price: the actual price
        """
        trading_rule = self._trading_rules[trading_pair]
        return trading_rule.min_price_increment

    def get_order_size_quantum(self, trading_pair: str, order_size: Decimal) -> Decimal:
        """
        Returns an order amount step, a minimum amount increment for a given trading pair.
        :param trading_pair: trading pair for which the size quantum will be calculated
        :param order_size: the actual amount
        """
        trading_rule = self._trading_rules[trading_pair]
        return Decimal(trading_rule.min_base_amount_increment)

    def start_tracking_order(self, order_id: str, exchange_order_id: str, trading_pair: str, trading_type: object,
                             price: object, amount: object, order_type: object, leverage: int, position: str):
        self._in_flight_orders[order_id] = BybitPerpetualInFlightOrder(
            client_order_id=order_id,
            exchange_order_id=exchange_order_id,
            trading_pair=trading_pair,
            order_type=order_type,
            trade_type=trading_type,
            price=price,
            amount=amount,
            leverage=leverage,
            position=position)

    def stop_tracking_order(self, order_id: str):
        """
        Stops tracking an order by simply removing it from _in_flight_orders dictionary.
        :param order_id" client order id of the order that should no longer be tracked
        """
        if order_id in self._in_flight_orders:
            del self._in_flight_orders[order_id]

    async def _create_order(self,
                            trade_type: TradeType,
                            order_id: str,
                            trading_pair: str,
                            amount: Decimal,
                            position_action: PositionAction,
                            price: Decimal = s_decimal_0,
                            order_type: OrderType = OrderType.MARKET):
        """
        Calls create-order API end point to place an order, starts tracking the order and triggers order created event.
        :param trade_type: BUY or SELL
        :param order_id: Internal order id (also called client_order_id)
        :param trading_pair: The market to place order
        :param amount: The order amount (in base token value)
        :param amount: Action to take for the position (OPEN or CLOSE)
        :param price: The order price
        :param order_type: The order type
        """
        trading_rule: TradingRule = self._trading_rules[trading_pair]

        if position_action not in [PositionAction.OPEN, PositionAction.CLOSE]:
            raise ValueError("Specify either OPEN_POSITION or CLOSE_POSITION position_action to create an order")

        try:
            amount: Decimal = self.quantize_order_amount(trading_pair, amount)
            if amount < trading_rule.min_order_size:
                raise ValueError(f"{trade_type.name} order amount {amount} is lower than the minimum order size "
                                 f"{trading_rule.min_order_size}.")

            params = {
                "side": "Buy" if trade_type == TradeType.BUY else "Sell",
                "symbol": await self._trading_pair_symbol(trading_pair),
                "qty": amount,
                "time_in_force": self._DEFAULT_TIME_IN_FORCE,
                "order_link_id": order_id,
            }

            if order_type.is_limit_type():
                price: Decimal = self.quantize_order_price(trading_pair, price)
                params.update({
                    "order_type": "Limit",
                    "price": price,
                })
            else:
                params.update({
                    "order_type": "Market"
                })

            self.start_tracking_order(order_id,
                                      None,
                                      trading_pair,
                                      trade_type,
                                      price,
                                      amount,
                                      order_type,
                                      self.get_leverage(trading_pair),
                                      position_action.name)

            send_order_results = await self._api_request(
                method="POST",
                path_url=CONSTANTS.PLACE_ACTIVE_ORDER_ENDPOINT,
                body=params,
                is_auth_required=True
            )

            if send_order_results["ret_code"] != 0:
                raise ValueError(f"Order is rejected by the API. "
                                 f"Parameters: {params} Error Msg: {send_order_results['ret_msg']}")

            result = send_order_results["result"]
            exchange_order_id = str(result["order_id"])

            tracked_order = self._in_flight_orders.get(order_id)
            if tracked_order is not None:
                self.logger().info(f"Created {order_type.name} {trade_type.name} order {order_id} for "
                                   f"{amount} {trading_pair}.")
                tracked_order.update_exchange_order_id(exchange_order_id)

            # TODO the event should be triggered once the order creation is confirmed by the exchange
            # since they process requests asynchronously

            # event_tag = MarketEvent.BuyOrderCreated if trade_type is TradeType.BUY else MarketEvent.SellOrderCreated
            # event_class = BuyOrderCreatedEvent if trade_type is TradeType.BUY else SellOrderCreatedEvent
            # self.trigger_event(event_tag,
            #                    event_class(
            #                        self.current_timestamp,
            #                        order_type,
            #                        trading_pair,
            #                        amount,
            #                        price,
            #                        order_id,
            #                        leverage=self.get_leverage(trading_pair),
            #                        position=position_action.name
            #                    ))

        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.stop_tracking_order(order_id)
            self.trigger_event(MarketEvent.OrderFailure,
                               MarketOrderFailureEvent(self.current_timestamp, order_id, order_type))
            self.logger().network(
                f"Error submitting {trade_type.name} {order_type.name} order to Bybit Perpetual for "
                f"{amount} {trading_pair} {price}. Error: {str(e)}",
                exc_info=True,
                app_warning_msg="Error submitting order to Bybit Perpetual. "
            )

    def buy(self, trading_pair: str, amount: Decimal, order_type: OrderType = OrderType.MARKET,
            price: Decimal = s_decimal_NaN, **kwargs) -> str:
        """
        Buys an amount of base asset as specified in the trading pair. This function returns immediately.
        To see an actual order, wait for a BuyOrderCreatedEvent.
        :param trading_pair: The market (e.g. BTC-CAD) to buy from
        :param amount: The amount in base token value
        :param order_type: The order type
        :param price: The price in which the order is to be placed at
        :returns: A new client order id
        """
        order_id: str = bybit_utils.get_new_client_order_id(True, trading_pair)
        safe_ensure_future(self._create_order(trade_type=TradeType.BUY,
                                              trading_pair=trading_pair,
                                              order_id=order_id,
                                              amount=amount,
                                              price=price,
                                              order_type=order_type,
                                              position_action=kwargs["position_action"]
                                              ))
        return order_id

    def sell(self, trading_pair: str, amount: Decimal, order_type: OrderType = OrderType.MARKET,
             price: Decimal = s_decimal_NaN, **kwargs) -> str:
        """
        Sells an amount of base asset as specified in the trading pair. This function returns immediately.
        To see an actual order, wait for a BuyOrderCreatedEvent.
        :param trading_pair: The market (e.g. BTC-CAD) to buy from
        :param amount: The amount in base token value
        :param order_type: The order type
        :param price: The price in which the order is to be placed at
        :returns: A new client order id
        """
        order_id: str = bybit_utils.get_new_client_order_id(False, trading_pair)
        safe_ensure_future(self._create_order(trade_type=TradeType.SELL,
                                              trading_pair=trading_pair,
                                              order_id=order_id,
                                              amount=amount,
                                              price=price,
                                              order_type=order_type,
                                              position_action=kwargs["position_action"]
                                              ))
        return order_id

    def trigger_order_created_event(self, order: BybitPerpetualInFlightOrder):
        event_tag = MarketEvent.BuyOrderCreated if order.trade_type is TradeType.BUY else MarketEvent.SellOrderCreated
        event_class = BuyOrderCreatedEvent if order.trade_type is TradeType.BUY else SellOrderCreatedEvent
        self.trigger_event(event_tag,
                           event_class(
                               self.current_timestamp,
                               order.order_type,
                               order.trading_pair,
                               order.amount,
                               order.price,
                               order.client_order_id,
                               exchange_order_id=order.exchange_order_id,
                               leverage=self._leverage[order.trading_pair],
                               position=order.position
                           ))

    async def _execute_cancel(self, trading_pair: str, order_id: str) -> str:
        """
        Executes order cancellation process by first calling the CancelOrder endpoint. The API response simply verifies
        that the API request have been received by the API servers. To determine if an order is successfully cancelled,
        we either call the GetOrderStatus/GetOpenOrders endpoint or wait for a OrderStateEvent/OrderTradeEvent from the WS.
        :param trading_pair: The market (e.g. BTC-CAD) the order is in.
        :param order_id: The client_order_id of the order to be cancelled.
        """
        try:
            tracked_order: Optional[BybitPerpetualInFlightOrder] = self._in_flight_orders.get(order_id, None)
            if tracked_order is None:
                raise ValueError(f"Order {order_id} is not being tracked")

            body_params = {
                "symbol": await self._trading_pair_symbol(trading_pair),
                "order_link_id": tracked_order.client_order_id
            }
            if tracked_order.exchange_order_id:
                body_params["order_id"] = tracked_order.exchange_order_id

            # The API response simply verifies that the API request have been received by the API servers.
            response = await self._api_request(
                method="POST",
                path_url=CONSTANTS.CANCEL_ACTIVE_ORDER_ENDPOINT,
                body=body_params,
                is_auth_required=True
            )

            if response["ret_code"] != 0:
                raise IOError(f"Bybit Perpetual encountered a problem cancelling the order"
                              f" ({response['ret_code']} - {response['ret_msg']})")

            return order_id

        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.logger().error(f"Failed to cancel order {order_id}: {str(e)}")
            self.logger().network(
                f"Failed to cancel order {order_id}: {str(e)}",
                exc_info=True,
                app_warning_msg=f"Failed to cancel order {order_id} on NDAX. "
                                f"Check API key and network connection."
            )

    def cancel(self, trading_pair: str, order_id: str):
        """
        Cancel an order. This function returns immediately.
        An Order is only determined to be cancelled when a OrderCancelledEvent is received.
        :param trading_pair: The market (e.g. BTC-CAD) of the order.
        :param order_id: The client_order_id of the order to be cancelled.
        """
        safe_ensure_future(self._execute_cancel(trading_pair, order_id))
        return order_id

    async def cancel_all(self, timeout_seconds: float) -> List[CancellationResult]:
        """
        Async function that cancels all active orders.
        Used by bot's top level stop and exit commands (cancelling outstanding orders on exit)
        :returns: List of CancellationResult which indicates whether each order is successfully cancelled.
        """
        tasks = []
        order_id_set = set()
        for order in self._in_flight_orders.values():
            if not order.is_done:
                order_id_set.add(order.client_order_id)
                tasks.append(asyncio.get_event_loop().create_task(
                    self._execute_cancel(order.trading_pair, order.client_order_id)))
        successful_cancellations = []

        try:
            results = await asyncio.wait_for(
                asyncio.shield(safe_gather(*tasks, return_exceptions=True)),
                timeout_seconds)
            for result in results:
                if result is not None:
                    order_id_set.remove(result)
                    successful_cancellations.append(CancellationResult(result, True))
        except asyncio.TimeoutError:
            self.logger().warning("Cancellation of all active orders for Bybit Perpetual connector"
                                  " stopped after max wait time")

        failed_cancellations = [CancellationResult(oid, False) for oid in order_id_set]
        return successful_cancellations + failed_cancellations

    def tick(self, timestamp: float):
        """
        Is called automatically by the clock for each clock tick(1 second by default).
        It checks if a status polling task is due for execution.
        """
        now = time.time()
        poll_interval = (self.SHORT_POLL_INTERVAL
                         if now - self._user_stream_tracker.last_recv_time > 60.0
                         else self.LONG_POLL_INTERVAL)
        last_tick = int(self._last_timestamp / poll_interval)
        current_tick = int(timestamp / poll_interval)
        if current_tick > last_tick:
            if not self._poll_notifier.is_set():
                self._poll_notifier.set()
        self._last_timestamp = timestamp

    def get_fee(self,
                base_currency: str,
                quote_currency: str,
                order_type: OrderType,
                order_side: TradeType,
                amount: Decimal,
                price: Decimal = s_decimal_NaN) -> TradeFee:
        """
        To get trading fee, this function is simplified by using fee override configuration. Most parameters to this
        function are ignore except order_type. Use OrderType.LIMIT_MAKER to specify you want trading fee for
        maker order.
        """
        is_maker = order_type is OrderType.LIMIT
        return TradeFee(percent=self.estimate_fee_pct(is_maker))

    def _format_trading_rules(self, instrument_info: List[Dict[str, Any]]) -> Dict[str, TradingRule]:
        """
        Converts JSON API response into a local dictionary of trading rules.
        :param instrument_info: The JSON API response.
        :returns: A dictionary of trading pair to its respective TradingRule.
        """
        trading_rules = {}
        for instrument in instrument_info:
            try:
                trading_pair = f"{instrument['base_currency']}-{instrument['quote_currency']}"
                trading_rules[trading_pair] = TradingRule(
                    trading_pair=trading_pair,
                    min_order_size=Decimal(str(instrument["lot_size_filter"]["min_trading_qty"])),
                    max_order_size=Decimal(str(instrument["lot_size_filter"]["max_trading_qty"])),
                    min_price_increment=Decimal(str(instrument["price_filter"]["tick_size"])),
                    min_base_amount_increment=Decimal(str(instrument["lot_size_filter"]["qty_step"])),
                )
            except Exception:
                self.logger().error(f"Error parsing the trading pair rule: {instrument}. Skipping...",
                                    exc_info=True)
        return trading_rules

    async def _update_trading_rules(self):
        params = {}
        symbols_response: Dict[str, Any] = await self._api_request(
            method="GET",
            path_url=CONSTANTS.QUERY_SYMBOL_ENDPOINT,
            params=params
        )
        self._trading_rules.clear()
        self._trading_rules = self._format_trading_rules(symbols_response["result"])

    async def _trading_rules_polling_loop(self):
        """
        Periodically update trading rules.
        """
        while True:
            try:
                await self._update_trading_rules()
                await asyncio.sleep(self.UPDATE_TRADING_RULES_INTERVAL)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger().network(f"Unexpected error while fetching trading rules. Error: {str(e)}",
                                      exc_info=True,
                                      app_warning_msg="Could not fetch new trading rules from Bybit Perpetual. "
                                                      "Check network connection.")
                await asyncio.sleep(0.5)

    async def _update_balances(self):
        """
        Calls REST API to update total and available balances
        """
        local_asset_names = set(self._account_balances.keys())
        remote_asset_names = set()

        params = {}
        account_positions: Dict[str, Dict[str, Any]] = await self._api_request(
            method="GET",
            path_url=CONSTANTS.GET_WALLET_BALANCE_ENDPOINT,
            params=params,
            is_auth_required=True
        )

        for asset_name, balance_json in account_positions["result"].items():
            self._account_balances[asset_name] = Decimal(str(balance_json["wallet_balance"]))
            self._account_available_balances[asset_name] = Decimal(str(balance_json["available_balance"]))
            remote_asset_names.add(asset_name)

        asset_names_to_remove = local_asset_names.difference(remote_asset_names)
        for asset_name in asset_names_to_remove:
            del self._account_available_balances[asset_name]
            del self._account_balances[asset_name]

    async def _update_order_status(self):
        """
        Calls REST API to get order status
        """

        active_orders: List[BybitPerpetualInFlightOrder] = [
            o for o in self._in_flight_orders.values()
            if not o.is_created
        ]

        tasks = []
        for active_order in active_orders:
            query_params = {
                "symbol": await self._trading_pair_symbol(active_order.trading_pair),
                "order_link_id": active_order.client_order_id
            }
            if active_order.exchange_order_id is not None:
                query_params["order_id"] = active_order.exchange_order_id

            tasks.append(
                asyncio.create_task(self._api_request(method="GET",
                                                      path_url=CONSTANTS.QUERY_ACTIVE_ORDER_ENDPOINT,
                                                      params=query_params,
                                                      is_auth_required=True,
                                                      )))
        self.logger().debug(f"Polling for order status updates of {len(tasks)} orders.")

        raw_responses: List[Dict[str, Any]] = await safe_gather(*tasks, return_exceptions=True)

        # Initial parsing of responses. Removes Exceptions.
        parsed_status_responses: List[Dict[str, Any]] = []
        for resp in raw_responses:
            if not isinstance(resp, Exception):
                parsed_status_responses.append(resp["result"])
            else:
                self.logger().error(f"Error fetching order status. Response: {resp}")

        for order_status in parsed_status_responses:
            self._process_order_event_message(order_status)

    async def _status_polling_loop(self):
        """
        Periodically update user balances and order status via REST API. This serves as a fallback measure for web
        socket API updates.
        """
        while True:
            try:
                self._poll_notifier = asyncio.Event()
                await self._poll_notifier.wait()
                start_ts = self.current_timestamp
                await safe_gather(
                    self._update_balances(),
                    # self._update_positions(),
                    self._update_order_status(),
                    self._update_trade_history(),
                )
                self._last_poll_timestamp = start_ts
            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger().error(f"Unexpected error while in status polling loop. Error: {str(e)}", exc_info=True)
                self.logger().network("Unexpected error while fetching account updates.",
                                      exc_info=True,
                                      app_warning_msg="Could not fetch account updates from Bybit Perpetual. "
                                                      "Check API key and network connection.")
                await asyncio.sleep(0.5)

    def _process_order_event_message(self, order_msg: Dict[str, Any]):
        """
        Updates in-flight order and triggers cancellation or failure event if needed.
        :param order_msg: The order event message payload
        """
        client_order_id = str(order_msg["order_link_id"])

        if client_order_id in self.in_flight_orders:
            tracked_order = self.in_flight_orders[client_order_id]
            was_created = tracked_order.is_created

            # Update order execution status
            tracked_order.last_state = order_msg["order_status"]

            if was_created and tracked_order.is_new:
                self.trigger_order_created_event(tracked_order)
            elif tracked_order.is_cancelled:
                self.logger().info(f"Successfully cancelled order {client_order_id}")
                self.trigger_event(MarketEvent.OrderCancelled,
                                   OrderCancelledEvent(
                                       self.current_timestamp,
                                       client_order_id))
                self.stop_tracking_order(client_order_id)
            elif tracked_order.is_failure:
                self.logger().info(f"The market order {client_order_id} has failed according to order status event. "
                                   f"Reason: {order_msg['reject_reason']}")
                self.trigger_event(MarketEvent.OrderFailure,
                                   MarketOrderFailureEvent(
                                       self.current_timestamp,
                                       client_order_id,
                                       tracked_order.order_type
                                   ))
                self.stop_tracking_order(client_order_id)

    async def _funding_info_polling_loop(self):
        """
        Retrieves funding information periodically. Tends to only update every set interval(i.e. 8hrs).
        Updates _funding_info variable.
        """
        while True:
            try:
                # TODO: Confirm the appropriate time interval
                for trading_pair in self._trading_pairs:
                    if trading_pair not in BybitPerpetualAPIOrderBookDataSource._trading_pair_symbol_map:
                        self.logger().error(f"Trading pair {trading_pair} not supported.")
                        raise ValueError(f"Trading pair {trading_pair} not supported.")
                    params = {
                        "symbol": BybitPerpetualAPIOrderBookDataSource._trading_pair_symbol_map[trading_pair]
                    }
                    resp = await self._api_request(method="GET",
                                                   path_url=CONSTANTS.LATEST_SYMBOL_INFORMATION_ENDPOINT,
                                                   params=params)

                    self._funding_info[trading_pair] = FundingInfo(
                        trading_pair=trading_pair,
                        index_price=Decimal(str(resp["index_price"])),
                        mark_price=Decimal(str(resp["mark_price"])),
                        next_funding_utc_timestamp=resp["next_funding_time"],
                        rate=Decimal(str(resp["funding_rate"]))
                        # TODO: Confirm whether to use funding_rate or predicted_funding_rate
                    )

            except asyncio.CancelledError:
                raise
            except Exception as e:
                self.logger().error(f"Unexpected error updating funding info. Error: {e}. Retrying in 10 seconds... ",
                                    exc_info=True)

    async def _user_funding_fee_polling_loop(self):
        """
        Retrieve User Funding Fee every Funding Time(every 8hrs). Trigger FundingPaymentCompleted event as required.
        """
        pass
