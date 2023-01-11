import asyncio
import unittest
from typing import Awaitable, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from hummingbot.client.config.client_config_map import ClientConfigMap
from hummingbot.client.config.config_helpers import ClientConfigAdapter
from hummingbot.connector.derivative.dydx_perpetual.dydx_perpetual_derivative import DydxPerpetualDerivative
from hummingbot.connector.test_support.network_mocking_assistant import NetworkMockingAssistant


class DydxPerpetualUserStreamDataSourceUnitTests(unittest.TestCase):
    # logging.Level required to receive logs from the data source logger
    level = 0

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.ev_loop = asyncio.get_event_loop()

        cls.base_asset = "COINALPHA"
        cls.quote_asset = "HBOT"
        cls.trading_pair = f"{cls.base_asset}-{cls.quote_asset}"
        cls.ex_trading_pair = f"{cls.base_asset}-{cls.quote_asset}"

    def setUp(self) -> None:
        super().setUp()

        self.log_records = []
        self.async_task: Optional[asyncio.Task] = None

        client_config_map = ClientConfigAdapter(ClientConfigMap())
        self.connector = DydxPerpetualDerivative(
            client_config_map,
            dydx_perpetual_api_key="someApiKey",
            dydx_perpetual_api_secret="AA1p9oklqBkDT8xw2FRWwlZCfUf98wEG",
            dydx_perpetual_passphrase="somePassphrase",
            dydx_perpetual_ethereum_address="someEthAddress",
            dydx_perpetual_stark_private_key="0123456789",
            trading_pairs=[self.trading_pair],
            trading_required=False,
        )

        self.data_source = self.connector._create_user_stream_data_source()

        self.data_source.logger().setLevel(1)
        self.data_source.logger().addHandler(self)

        self.mocking_assistant = NetworkMockingAssistant()
        self.resume_test_event = asyncio.Event()

    def tearDown(self) -> None:
        self.async_task and self.async_task.cancel()
        super().tearDown()

    def handle(self, record):
        self.log_records.append(record)

    def _is_logged(self, log_level: str, message: str) -> bool:
        return any(record.levelname == log_level and record.getMessage() == message for record in self.log_records)

    def _create_exception_and_unlock_test_with_event(self, exception):
        self.resume_test_event.set()
        raise exception

    def async_run_with_timeout(self, coroutine: Awaitable, timeout: float = 1):
        ret = self.ev_loop.run_until_complete(asyncio.wait_for(coroutine, timeout))
        return ret

    @patch("aiohttp.ClientSession.ws_connect", new_callable=AsyncMock)
    @patch(
        "hummingbot.connector.derivative.dydx_perpetual.dydx_perpetual_user_stream_data_source."
        "DydxPerpetualUserStreamDataSource._sleep"
    )
    def test_listen_for_user_stream_raises_cancelled_exception(self, _, ws_connect_mock):
        ws_connect_mock.side_effect = asyncio.CancelledError

        with self.assertRaises(asyncio.CancelledError):
            self.async_run_with_timeout(self.data_source.listen_for_user_stream(asyncio.Queue()))

    @patch("aiohttp.ClientSession.ws_connect", new_callable=AsyncMock)
    @patch("hummingbot.connector.derivative.dydx_perpetual.dydx_perpetual_auth.DydxPerpetualAuth._get_iso_timestamp")
    @patch(
        "hummingbot.connector.derivative.dydx_perpetual.dydx_perpetual_user_stream_data_source."
        "DydxPerpetualUserStreamDataSource._sleep"
    )
    def test_listen_for_user_stream_raises_logs_exception(self, mock_sleep, ts_mock, ws_connect_mock):
        mock_sleep.side_effect = lambda: (self.ev_loop.run_until_complete(asyncio.sleep(0.5)))
        ts_mock.return_value = "2022-07-06T12:20:53.000Z"
        ws_connect_mock.return_value = self.mocking_assistant.create_websocket_mock()
        ws_connect_mock.return_value.receive.side_effect = lambda *_: self._create_exception_and_unlock_test_with_event(
            Exception("TEST ERROR")
        )
        self.async_task = self.ev_loop.create_task(self.data_source.listen_for_user_stream(asyncio.Queue()))

        self.async_run_with_timeout(self.resume_test_event.wait(), 1.0)

        self.assertTrue(
            self._is_logged("ERROR", "Unexpected error while listening to user stream. Retrying after 5 seconds...")
        )

    @patch("aiohttp.ClientSession.ws_connect", new_callable=AsyncMock)
    @patch("hummingbot.connector.derivative.dydx_perpetual.dydx_perpetual_auth.DydxPerpetualAuth._get_iso_timestamp")
    def test_ws_authentication_successful(self, ts_mock: MagicMock, ws_connect_mock):
        ts_mock.return_value = "2022-07-06T12:20:53.000Z"

        ws_connect_mock.return_value = self.mocking_assistant.create_websocket_mock()
        self.async_run_with_timeout(self.data_source._connected_websocket_assistant())

        json_msgs = self.mocking_assistant.json_messages_sent_through_websocket(ws_connect_mock.return_value)

        self.assertEqual("someApiKey", json_msgs[0]["apiKey"])
        self.assertEqual("somePassphrase", json_msgs[0]["passphrase"])
        self.assertEqual(ts_mock.return_value, json_msgs[0]["timestamp"])
        self.assertEqual("MLJvgJDWv-o1lz1e6oRuU96SbCay1Qo9m-E6kKleOxY=", json_msgs[0]["signature"])
