#!/usr/bin/env python
import time
import asyncio
import logging
from typing import (
    Any,
    AsyncIterable,
    List,
    Optional,
)
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.logger import HummingbotLogger
from .gate_io_constants import Constants
from .gate_io_auth import GateIoAuth
from .gate_io_utils import GateIoAPIError
from .gate_io_websocket import GateIoWebsocket


class GateIoAPIUserStreamDataSource(UserStreamTrackerDataSource):

    _logger: Optional[HummingbotLogger] = None

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._logger is None:
            cls._logger = logging.getLogger(__name__)
        return cls._logger

    def __init__(self, gate_io_auth: GateIoAuth, trading_pairs: Optional[List[str]] = []):
        self._gate_io_auth: GateIoAuth = gate_io_auth
        self._ws: GateIoWebsocket = None
        self._trading_pairs = trading_pairs
        self._current_listen_key = None
        self._listen_for_user_stream_task = None
        self._last_recv_time: float = 0
        super().__init__()

    @property
    def last_recv_time(self) -> float:
        return self._last_recv_time

    async def _ws_request_balances(self):
        return await self._ws.request(Constants.WS_METHODS["USER_BALANCE"])

    async def _listen_to_orders_trades_balances(self) -> AsyncIterable[Any]:
        """
        Subscribe to active orders via web socket
        """

        try:
            self._ws = GateIoWebsocket(self._gate_io_auth)

            await self._ws.connect()

            await self._ws.subscribe(Constants.WS_SUB["USER_ORDERS_TRADES"], None, {})

            event_methods = [
                Constants.WS_METHODS["USER_ORDERS"],
                Constants.WS_METHODS["USER_TRADES"],
            ]

            async for msg in self._ws.on_message():
                if msg is None:
                    # Skip empty subscribed/unsubscribed messages
                    continue
                self._last_recv_time = time.time()

                if msg.get("params", msg.get("result", None)) is None:
                    continue
                elif msg.get("method", None) in event_methods:
                    await self._ws_request_balances()
                yield msg
        except Exception as e:
            raise e
        finally:
            await self._ws.disconnect()
            await asyncio.sleep(5)

    async def listen_for_user_stream(self, ev_loop: asyncio.BaseEventLoop, output: asyncio.Queue) -> AsyncIterable[Any]:
        """
        *required
        Subscribe to user stream via web socket, and keep the connection open for incoming messages
        :param ev_loop: ev_loop to execute this function in
        :param output: an async queue where the incoming messages are stored
        """

        while True:
            try:
                async for msg in self._listen_to_orders_trades_balances():
                    output.put_nowait(msg)
            except asyncio.CancelledError:
                raise
            except GateIoAPIError as e:
                self.logger().error(e.error_payload.get('error'), exc_info=True)
                raise
            except Exception:
                self.logger().error(
                    f"Unexpected error with {Constants.EXCHANGE_NAME} WebSocket connection. "
                    "Retrying after 30 seconds...", exc_info=True)
                await asyncio.sleep(30.0)
