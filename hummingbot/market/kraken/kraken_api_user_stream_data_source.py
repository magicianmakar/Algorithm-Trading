#!/usr/bin/env python

import asyncio
import aiohttp
import logging
from typing import (
    AsyncIterable,
    Dict,
    Optional,
    Any
)
import ujson
import websockets
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.logger import HummingbotLogger
from hummingbot.market.kraken.kraken_auth import KrakenAuth
from hummingbot.market.kraken.kraken_order_book import KrakenOrderBook

KRAKEN_WS_URL = "wss://ws-auth.kraken.com/"

KRAKEN_ROOT_API = "https://api.kraken.com"
GET_TOKEN_URI = "/0/private/GetWebSocketsToken"


class KrakenAPIUserStreamDataSource(UserStreamTrackerDataSource):

    MESSAGE_TIMEOUT = 3.0
    PING_TIMEOUT = 5.0

    _krausds_logger: Optional[HummingbotLogger] = None

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._krausds_logger is None:
            cls._krausds_logger = logging.getLogger(__name__)
        return cls._krausds_logger

    def __init__(self, kraken_auth: KrakenAuth):
        self._kraken_auth: KrakenAuth = kraken_auth
        self._shared_client: Optional[aiohttp.ClientSession] = None
        self._current_auth_token: Optional[str] = None
        super().__init__()
    
    @property
    def order_book_class(self):
        return KrakenOrderBook

    async def get_auth_token(self) -> str:
        api_auth: Dict[str, Any] = self._kraken_auth.generate_auth_dict(uri=GET_TOKEN_URI)

        client: aiohttp.ClientSession = await self._http_client()

        response_coro = client.request(
            method=method.upper(),
            url=KRAKEN_ROOT_API + GET_TOKEN_URI,
            headers=api_auth["headers"],
            data=api_auth["postDict"],
            timeout=100
        )

        async with response_coro as response:
            if response.status != 200:
                raise IOError(f"Error fetching Kraken user stream listen key. HTTP status is {response.status}.")

            try:
                response_json: Dict[str, Any] = await response.json()
            except Exception:
                raise IOError(f"Error parsing data from {url}.")

            return response_json["result"]["token"]

    async def listen_for_user_stream(self, ev_loop: asyncio.BaseEventLoop, output: asyncio.Queue):
        while True:
            try:
                async with websockets.connect(KRAKEN_WS_URL) as ws:
                    ws: websockets.WebSocketClientProtocol = ws

                    if self._current_auth_token is None:
                        self._current_auth_token = await self.get_auth_token()

                    for subscription_type in ["openOrders"]:
                        subscribe_request: Dict[str, Any] = {
                            "event": "subscribe",
                            "subscription": {
                                "name": subscription_type,
                                "token": self._current_auth_token
                            }
                        }
                        await ws.send(ujson.dumps(subscribe_request))

                    async for raw_msg in self._inner_messages(ws):
                        diff_msg = ujson.loads(raw_msg)
                        output.put_nowait(diff_msg)
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger().error("Unexpected error with Kraken WebSocket connection. "
                                    "Retrying after 30 seconds...", exc_info=True)
                self._current_auth_token = None
                await asyncio.sleep(30.0)

    async def _http_client(self) -> aiohttp.ClientSession:
        if self._shared_client is None:
            self._shared_client = aiohttp.ClientSession()
        return self._shared_client

    async def _inner_messages(self,
                              ws: websockets.WebSocketClientProtocol) -> AsyncIterable[str]:
        """
        Generator function that returns messages from the web socket stream
        :param ws: current web socket connection
        :returns: message in AsyncIterable format
        """
        # Terminate the recv() loop as soon as the next message timed out, so the outer loop can reconnect.
        try:
            while True:
                try:
                    msg: str = await asyncio.wait_for(ws.recv(), timeout=MESSAGE_TIMEOUT)
                    yield msg
                except asyncio.TimeoutError:
                    try:
                        pong_waiter = await ws.ping()
                        await asyncio.wait_for(pong_waiter, timeout=PING_TIMEOUT)
                    except asyncio.TimeoutError:
                        raise
        except asyncio.TimeoutError:
            self.logger().warning("WebSocket ping timed out. Going to reconnect...")
            return
        finally:
            await ws.close()
