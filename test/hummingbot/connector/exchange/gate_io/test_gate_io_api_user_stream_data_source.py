import asyncio
import json
import unittest
from test.hummingbot.connector.network_mocking_assistant import NetworkMockingAssistant
from typing import Awaitable, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from bidict import bidict

from hummingbot.connector.exchange.gate_io import gate_io_constants as CONSTANTS
from hummingbot.connector.exchange.gate_io import gate_io_web_utils as web_utils
from hummingbot.connector.exchange.gate_io.gate_io_api_order_book_data_source import GateIoAPIOrderBookDataSource
from hummingbot.connector.exchange.gate_io.gate_io_api_user_stream_data_source import GateIoAPIUserStreamDataSource
from hummingbot.connector.exchange.gate_io.gate_io_auth import GateIoAuth
from hummingbot.connector.time_synchronizer import TimeSynchronizer
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler


class TestGateIoAPIUserStreamDataSource(unittest.TestCase):
    # the level is required to receive logs from the data source logger
    level = 0

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.ev_loop = asyncio.get_event_loop()
        cls.base_asset = "COINALPHA"
        cls.quote_asset = "HBOT"
        cls.trading_pair = f"{cls.base_asset}-{cls.quote_asset}"
        cls.ex_trading_pair = f"{cls.base_asset}_{cls.quote_asset}"
        cls.api_key = "someKey"
        cls.api_secret_key = "someSecretKey"

    def setUp(self) -> None:
        super().setUp()
        self.log_records = []
        self.listening_task: Optional[asyncio.Task] = None
        self.mocking_assistant = NetworkMockingAssistant()

        self.throttler = AsyncThrottler(CONSTANTS.RATE_LIMITS)
        self.mock_time_provider = MagicMock()
        self.mock_time_provider.time.return_value = 1000
        self.auth = GateIoAuth(
            api_key=self.api_key,
            secret_key=self.api_secret_key,
            time_provider=self.mock_time_provider)
        self.time_synchronizer = TimeSynchronizer()
        self.time_synchronizer.add_time_offset_ms_sample(0)

        self.api_factory = web_utils.build_api_factory(
            throttler=self.throttler,
            time_synchronizer=self.time_synchronizer,
            auth=self.auth)
        self.data_source = GateIoAPIUserStreamDataSource(
            self.auth,
            trading_pairs=[self.trading_pair],
            api_factory=self.api_factory,
            throttler=self.throttler,
            time_synchronizer=self.time_synchronizer)

        self.data_source.logger().setLevel(1)
        self.data_source.logger().addHandler(self)

        GateIoAPIOrderBookDataSource._trading_pair_symbol_map = {
            CONSTANTS.DEFAULT_DOMAIN: bidict(
                {self.ex_trading_pair: self.trading_pair})
        }

    def tearDown(self) -> None:
        GateIoAPIOrderBookDataSource._trading_pair_symbol_map = {}
        self.listening_task and self.listening_task.cancel()
        super().tearDown()

    def handle(self, record):
        self.log_records.append(record)

    def _is_logged(self, log_level: str, message: str) -> bool:
        return any(record.levelname == log_level and record.getMessage() == message
                   for record in self.log_records)

    def async_run_with_timeout(self, coroutine: Awaitable, timeout: int = 1):
        ret = self.ev_loop.run_until_complete(asyncio.wait_for(coroutine, timeout))
        return ret

    def test_last_recv_time(self):
        # Initial last_recv_time
        self.assertEqual(0, self.data_source.last_recv_time)

        ws_assistant = self.async_run_with_timeout(self.data_source._get_ws_assistant())
        ws_assistant._connection._last_recv_time = 1000
        self.assertEqual(1000, self.data_source.last_recv_time)

    @patch("aiohttp.ClientSession.ws_connect", new_callable=AsyncMock)
    @patch("hummingbot.connector.exchange.gate_io.gate_io_api_user_stream_data_source.GateIoAPIUserStreamDataSource"
           "._time")
    def test_listen_for_user_stream_subscribes_to_orders_and_balances_events(self, time_mock, ws_connect_mock):
        time_mock.return_value = 1000
        ws_connect_mock.return_value = self.mocking_assistant.create_websocket_mock()

        result_subscribe_orders = {
            "time": 1611541000,
            "channel": CONSTANTS.USER_ORDERS_ENDPOINT_NAME,
            "event": "subscribe",
            "error": None,
            "result": {
                "status": "success"
            }
        }
        result_subscribe_trades = {
            "time": 1611541000,
            "channel": CONSTANTS.USER_TRADES_ENDPOINT_NAME,
            "event": "subscribe",
            "error": None,
            "result": {
                "status": "success"
            }
        }
        result_subscribe_balance = {
            "time": 1611541000,
            "channel": CONSTANTS.USER_BALANCE_ENDPOINT_NAME,
            "event": "subscribe",
            "error": None,
            "result": {
                "status": "success"
            }
        }

        self.mocking_assistant.add_websocket_aiohttp_message(
            websocket_mock=ws_connect_mock.return_value,
            message=json.dumps(result_subscribe_orders))
        self.mocking_assistant.add_websocket_aiohttp_message(
            websocket_mock=ws_connect_mock.return_value,
            message=json.dumps(result_subscribe_trades))
        self.mocking_assistant.add_websocket_aiohttp_message(
            websocket_mock=ws_connect_mock.return_value,
            message=json.dumps(result_subscribe_balance))

        output_queue = asyncio.Queue()

        self.listening_task = self.ev_loop.create_task(self.data_source.listen_for_user_stream(output=output_queue))

        self.mocking_assistant.run_until_all_aiohttp_messages_delivered(ws_connect_mock.return_value)

        sent_subscription_messages = self.mocking_assistant.json_messages_sent_through_websocket(
            websocket_mock=ws_connect_mock.return_value)

        self.assertEqual(3, len(sent_subscription_messages))
        expected_orders_subscription = {
            "time": int(self.mock_time_provider.time()),
            "channel": CONSTANTS.USER_ORDERS_ENDPOINT_NAME,
            "event": "subscribe",
            "payload": [self.ex_trading_pair],
            "auth": {
                "KEY": self.api_key,
                "SIGN": '005d2e6996fa7783459453d36ff871d8d5cfe225a098f37ac234543811c79e3c' # noqa: mock
                        'db8f41684f3ad9491f65c15ed880ce7baee81f402eb1df56b1bba188c0e7838c', # noqa: mock
                "method": "api_key"},
        }
        self.assertEqual(expected_orders_subscription, sent_subscription_messages[0])
        expected_trades_subscription = {
            "time": int(self.mock_time_provider.time()),
            "channel": CONSTANTS.USER_TRADES_ENDPOINT_NAME,
            "event": "subscribe",
            "payload": [self.ex_trading_pair],
            "auth": {
                "KEY": self.api_key,
                "SIGN": '0f34bf79558905d2b5bc7790febf1099d38ff1aa39525a077db32bcbf9135268' # noqa: mock
                        'caf23cdf2d62315841500962f788f7c5f4c3f4b8a057b2184366687b1f74af69', # noqa: mock
                "method": "api_key"}
        }
        self.assertEqual(expected_trades_subscription, sent_subscription_messages[1])
        expected_balances_subscription = {
            "time": int(self.mock_time_provider.time()),
            "channel": CONSTANTS.USER_BALANCE_ENDPOINT_NAME,
            "event": "subscribe",
            "auth": {
                "KEY": self.api_key,
                "SIGN": '90f5e732fc586d09c4a1b7de13f65b668c7ce90678b30da87aa137364bac0b97' # noqa: mock
                        '16b34219b689fb754e821872933a0e12b1d415867b9fbb8ec441bc86e77fb79c', # noqa: mock
                "method": "api_key"}
        }
        self.assertEqual(expected_balances_subscription, sent_subscription_messages[2])

        self.assertTrue(self._is_logged(
            "INFO",
            "Subscribed to private order changes and balance updates channels..."
        ))

    @patch("aiohttp.ClientSession.ws_connect", new_callable=AsyncMock)
    @patch("hummingbot.connector.exchange.gate_io.gate_io_api_user_stream_data_source.GateIoAPIUserStreamDataSource"
           "._time")
    def test_listen_for_user_stream_skips_subscribe_unsubscribe_messages(self, time_mock, ws_connect_mock):
        time_mock.return_value = 1000
        ws_connect_mock.return_value = self.mocking_assistant.create_websocket_mock()

        result_subscribe_orders = {
            "time": 1611541000,
            "channel": CONSTANTS.USER_ORDERS_ENDPOINT_NAME,
            "event": "subscribe",
            "error": None,
            "result": {
                "status": "success"
            }
        }
        result_subscribe_trades = {
            "time": 1611541000,
            "channel": CONSTANTS.USER_TRADES_ENDPOINT_NAME,
            "event": "subscribe",
            "error": None,
            "result": {
                "status": "success"
            }
        }
        result_subscribe_balance = {
            "time": 1611541000,
            "channel": CONSTANTS.USER_BALANCE_ENDPOINT_NAME,
            "event": "subscribe",
            "error": None,
            "result": {
                "status": "success"
            }
        }

        self.mocking_assistant.add_websocket_aiohttp_message(
            websocket_mock=ws_connect_mock.return_value,
            message=json.dumps(result_subscribe_orders))
        self.mocking_assistant.add_websocket_aiohttp_message(
            websocket_mock=ws_connect_mock.return_value,
            message=json.dumps(result_subscribe_trades))
        self.mocking_assistant.add_websocket_aiohttp_message(
            websocket_mock=ws_connect_mock.return_value,
            message=json.dumps(result_subscribe_balance))

        output_queue = asyncio.Queue()

        self.listening_task = self.ev_loop.create_task(self.data_source.listen_for_user_stream(output=output_queue))

        self.mocking_assistant.run_until_all_aiohttp_messages_delivered(ws_connect_mock.return_value)

        self.assertTrue(output_queue.empty())

    @patch("aiohttp.ClientSession.ws_connect", new_callable=AsyncMock)
    def test_listen_for_user_stream_does_not_queue_pong_payload(self, mock_ws):
        mock_pong = {
            "time": 1545404023,
            "channel": CONSTANTS.PONG_CHANNEL_NAME,
            "event": "",
            "error": None,
            "result": None
        }

        mock_ws.return_value = self.mocking_assistant.create_websocket_mock()
        self.mocking_assistant.add_websocket_aiohttp_message(mock_ws.return_value, json.dumps(mock_pong))

        msg_queue = asyncio.Queue()
        self.listening_task = self.ev_loop.create_task(
            self.data_source.listen_for_user_stream(msg_queue)
        )

        self.mocking_assistant.run_until_all_aiohttp_messages_delivered(mock_ws.return_value)

        self.assertEqual(0, msg_queue.qsize())

    @patch("aiohttp.ClientSession.ws_connect", new_callable=AsyncMock)
    @patch("hummingbot.core.data_type.user_stream_tracker_data_source.UserStreamTrackerDataSource._sleep")
    def test_listen_for_user_stream_connection_failed(self, sleep_mock, mock_ws):
        mock_ws.side_effect = Exception("TEST ERROR.")
        sleep_mock.side_effect = asyncio.CancelledError  # to finish the task execution

        msg_queue = asyncio.Queue()
        try:
            self.async_run_with_timeout(self.data_source.listen_for_user_stream(msg_queue))
        except asyncio.CancelledError:
            pass

        self.assertTrue(
            self._is_logged("ERROR",
                            "Unexpected error occurred when listening to user streams. Retrying in 5 seconds..."))

    @patch("aiohttp.ClientSession.ws_connect", new_callable=AsyncMock)
    @patch("hummingbot.core.data_type.user_stream_tracker_data_source.UserStreamTrackerDataSource._sleep")
    def test_listen_for_user_stream_iter_message_throws_exception(self, sleep_mock, mock_ws):
        msg_queue: asyncio.Queue = asyncio.Queue()
        mock_ws.return_value = self.mocking_assistant.create_websocket_mock()
        mock_ws.return_value.receive.side_effect = Exception("TEST ERROR")
        sleep_mock.side_effect = asyncio.CancelledError  # to finish the task execution

        try:
            self.async_run_with_timeout(self.data_source.listen_for_user_stream(msg_queue))
        except asyncio.CancelledError:
            pass

        self.assertTrue(
            self._is_logged(
                "ERROR",
                "Unexpected error occurred when listening to user streams. Retrying in 5 seconds..."))
