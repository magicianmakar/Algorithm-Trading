#!/usr/bin/env python
import asyncio
import logging
from typing import Any, AsyncIterable, List, Optional

from hummingbot.connector.exchange.ascend_ex import ascend_ex_constants as CONSTANTS
from hummingbot.connector.exchange.ascend_ex.ascend_ex_auth import AscendExAuth
from hummingbot.connector.exchange.ascend_ex.ascend_ex_utils import get_ws_url_private
from hummingbot.connector.utils import build_api_factory
from hummingbot.core.api_throttler.async_throttler import AsyncThrottler
from hummingbot.core.data_type.user_stream_tracker_data_source import UserStreamTrackerDataSource
from hummingbot.core.web_assistant.connections.data_types import RESTMethod, RESTRequest, RESTResponse, WSRequest
from hummingbot.core.web_assistant.rest_assistant import RESTAssistant
from hummingbot.core.web_assistant.web_assistants_factory import WebAssistantsFactory
from hummingbot.core.web_assistant.ws_assistant import WSAssistant
from hummingbot.logger import HummingbotLogger


class AscendExAPIUserStreamDataSource(UserStreamTrackerDataSource):
    MAX_RETRIES = 20
    MESSAGE_TIMEOUT = 10.0
    PING_TIMEOUT = 5.0
    HEARTBEAT_PING_INTERVAL = 15.0

    _logger: Optional[HummingbotLogger] = None

    @classmethod
    def logger(cls) -> HummingbotLogger:
        if cls._logger is None:
            cls._logger = logging.getLogger(__name__)
        return cls._logger

    def __init__(
        self, ascend_ex_auth: AscendExAuth,
        api_factory: Optional[WebAssistantsFactory] = None,
        throttler: Optional[AsyncThrottler] = None,
        trading_pairs: Optional[List[str]] = None
    ):
        super().__init__()
        self._api_factory = api_factory or build_api_factory()
        self._throttler = throttler or self._get_throttler_instance()
        self._rest_assistant: Optional[RESTAssistant] = None
        self._ws_assistant: Optional[WSAssistant] = None
        self._ascend_ex_auth: AscendExAuth = ascend_ex_auth
        self._trading_pairs = trading_pairs or []
        self._current_listen_key = None
        self._listen_for_user_stream_task = None
        self._last_recv_time: float = 0

    @classmethod
    def _get_throttler_instance(cls) -> AsyncThrottler:
        throttler = AsyncThrottler(CONSTANTS.RATE_LIMITS)
        return throttler

    @property
    def last_recv_time(self) -> float:
        return self._last_recv_time

    async def listen_for_user_stream(self, ev_loop: asyncio.BaseEventLoop, output: asyncio.Queue) -> AsyncIterable[Any]:
        """
        *required
        Subscribe to user stream via web socket, and keep the connection open for incoming messages
        :param ev_loop: ev_loop to execute this function in
        :param output: an async queue where the incoming messages are stored
        """

        ws = None
        while True:
            try:
                headers = {
                    **self._ascend_ex_auth.get_headers(),
                    **self._ascend_ex_auth.get_auth_headers("info"),
                    **self._ascend_ex_auth.get_hb_id_headers(),
                }

                rest_assistant = await self._get_rest_assistant()
                url = f"{CONSTANTS.REST_URL}/{CONSTANTS.INFO_PATH_URL}"
                request = RESTRequest(method=RESTMethod.GET, url=url, headers=headers)

                async with self._throttler.execute_task(CONSTANTS.INFO_PATH_URL):
                    response: RESTResponse = await rest_assistant.call(request=request)

                info = await response.json()
                accountGroup = info.get("data").get("accountGroup")
                headers = {
                    **self._ascend_ex_auth.get_auth_headers("stream"),
                    **self._ascend_ex_auth.get_hb_id_headers(),
                }
                payload = {
                    "op": CONSTANTS.SUB_ENDPOINT_NAME,
                    "ch": "order:cash"
                }

                ws: WSAssistant = await self._get_ws_assistant()
                url = f"{get_ws_url_private(accountGroup)}/stream"
                await ws.connect(ws_url=url, ws_headers=headers, ping_timeout=self.HEARTBEAT_PING_INTERVAL)

                subscribe_request: WSRequest = WSRequest(payload)
                async with self._throttler.execute_task(CONSTANTS.SUB_ENDPOINT_NAME):
                    await ws.send(subscribe_request)

                async for raw_msg in ws.iter_messages():
                    msg = raw_msg.data
                    if msg is None:
                        continue
                    output.put_nowait(msg)
            except asyncio.CancelledError:
                raise
            except Exception:
                self.logger().error(
                    "Unexpected error with AscendEx WebSocket connection. " "Retrying after 30 seconds...",
                    exc_info=True
                )
                await asyncio.sleep(30.0)
            finally:
                ws and await ws.disconnect()

    async def _get_rest_assistant(self) -> RESTAssistant:
        if self._rest_assistant is None:
            self._rest_assistant = await self._api_factory.get_rest_assistant()
        return self._rest_assistant

    async def _get_ws_assistant(self) -> WSAssistant:
        if self._ws_assistant is None:
            self._ws_assistant = await self._api_factory.get_ws_assistant()
        return self._ws_assistant
