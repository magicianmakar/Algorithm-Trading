import asyncio
import unittest
from typing import Awaitable
from unittest.mock import patch, MagicMock

from hummingbot.client.config.global_config_map import global_config_map
from hummingbot.client.hummingbot_application import HummingbotApplication
from test.mock.mock_cli import CLIMockingAssistant


class StatusCommandTest(unittest.TestCase):
    @patch("hummingbot.core.utils.trading_pair_fetcher.TradingPairFetcher")
    def setUp(self, _: MagicMock) -> None:
        super().setUp()
        self.ev_loop = asyncio.get_event_loop()
        self.app = HummingbotApplication()
        self.cli_mock_assistant = CLIMockingAssistant()
        self.cli_mock_assistant.start()

    def tearDown(self) -> None:
        super().tearDown()
        self.cli_mock_assistant.stop()

    @staticmethod
    async def raise_timeout(*args, **kwargs):
        raise asyncio.TimeoutError

    def async_run_with_timeout(self, coroutine: Awaitable, timeout: float = 1):
        ret = self.ev_loop.run_until_complete(asyncio.wait_for(coroutine, timeout))
        return ret

    def async_run_with_timeout_coroutine_must_raise_timeout(self, coroutine: Awaitable, timeout: float = 1):
        class DesiredError(Exception):
            pass

        async def run_coro_that_raises(coro: Awaitable):
            try:
                await coro
            except asyncio.TimeoutError:
                raise DesiredError

        try:
            self.async_run_with_timeout(run_coro_that_raises(coroutine), timeout)
        except DesiredError:  # the coroutine raised an asyncio.TimeoutError as expected
            raise asyncio.TimeoutError
        except asyncio.TimeoutError:  # the coroutine did not finish on time
            raise RuntimeError

    @patch("hummingbot.client.command.status_command.StatusCommand.validate_required_connections")
    @patch("hummingbot.client.config.security.Security.is_decryption_done")
    def test_status_check_all_handles_network_timeouts(
        self, is_decryption_done_mock, validate_required_connections_mock
    ):
        validate_required_connections_mock.side_effect = self.raise_timeout
        is_decryption_done_mock.return_value = True
        global_config_map["other_commands_timeout"].value = 30
        strategy_name = "some-strategy"
        self.app.strategy_name = strategy_name
        self.app.strategy_file_name = f"{strategy_name}.yml"

        with self.assertRaises(asyncio.TimeoutError):
            self.async_run_with_timeout_coroutine_must_raise_timeout(self.app.status_check_all())
        self.assertTrue(
            self.cli_mock_assistant.check_log_called_with(
                msg="\nA network error prevented the connection check to complete. See logs for more details."
            )
        )
