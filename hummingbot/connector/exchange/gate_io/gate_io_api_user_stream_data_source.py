#!/usr/bin/env python
import asyncio
import logging
from typing import Any, AsyncIterable, List, Optional

from hummingbot.connector.exchange.gate_io import gate_io_constants as CONSTANTS
from hummingbot.connector.time_synchronizer import TimeSynchronizer
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.logger import HummingbotLogger

from .gate_io_auth import GateIoAuth
from . import gate_io_web_utils as web_utils


class GateIoAPIUserStreamDataSource(UserStreamTrackerDataSource):
    _logger: Optional[HummingbotLogger] = None

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._logger is None:
            cls._logger = logging.getLogger(__name__)
        return cls._logger

    def __init__(self,
                 auth,
                 domain: str,
                 trading_pairs: List[str],
                 api_factory: Optional[WebAssistantsFactory] = None,
                 throttler: Optional[AsyncThrottler] = None,
                 time_synchronizer: Optional[TimeSynchronizer] = None):
        self._api_factory = api_factory
        self._auth: GateIoAuth = auth
        self._ws: Optional[web_utils.GateIoWebsocket] = None
        self._trading_pairs: List[str] = trading_pairs
        self._current_listen_key = None
        self._listen_for_user_stream_task = None
        super().__init__()

    @property
    def last_recv_time(self) -> float:
        recv_time = 0
        if self._ws is not None:
            recv_time = self._ws.last_recv_time
        return recv_time

    async def _listen_to_orders_trades_balances(self) -> AsyncIterable[Any]:
        """
        Subscribe to active orders via web socket
        """
        try:
            self._ws = web_utils.GateIoWebsocket(self._auth, self._api_factory)
            await self._ws.connect()
            user_channels = [
                CONSTANTS.USER_TRADES_ENDPOINT_NAME,
                CONSTANTS.USER_ORDERS_ENDPOINT_NAME,
                CONSTANTS.USER_BALANCE_ENDPOINT_NAME,
            ]
            await self._ws.subscribe(CONSTANTS.USER_TRADES_ENDPOINT_NAME,
                                     [web_utils.convert_to_exchange_trading_pair(pair) for pair in self._trading_pairs])
            await self._ws.subscribe(CONSTANTS.USER_ORDERS_ENDPOINT_NAME,
                                     [web_utils.convert_to_exchange_trading_pair(pair) for pair in self._trading_pairs])
            await self._ws.subscribe(CONSTANTS.USER_BALANCE_ENDPOINT_NAME)

            async for msg in self._ws.on_message():
                if msg.get("event") in ["subscribe", "unsubscribe"]:
                    continue
                if msg.get("result", None) is None:
                    continue
                elif msg.get("channel", None) in user_channels:
                    yield msg
        except Exception as e:
            raise e
        finally:
            if self._ws is not None:
                await self._ws.disconnect()
            await self._sleep(5)

    async def listen_for_user_stream(self, output: asyncio.Queue):
        """
        *required
        Subscribe to user stream via web socket, and keep the connection open for incoming messages

        :param output: an async queue where the incoming messages are stored
        """

        while True:
            try:
                async for msg in self._listen_to_orders_trades_balances():
                    output.put_nowait(msg)
            except asyncio.CancelledError:
                raise
            except web_utils.APIError as e:
                self.logger().error(e.error_message, exc_info=True)
                raise
            except Exception:
                self.logger().error(
                    f"Unexpected error with {CONSTANTS.EXCHANGE_NAME} WebSocket connection. "
                    "Retrying after 30 seconds...", exc_info=True)
                await self._sleep(30)
