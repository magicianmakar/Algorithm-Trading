import unittest.mock
from decimal import Decimal
from test.hummingbot.strategy import assign_config_default

import hummingbot.strategy.cross_exchange_market_making.start as strategy_start
from hummingbot.client.config.client_config_map import ClientConfigMap
from hummingbot.client.config.config_helpers import ClientConfigAdapter
from hummingbot.connector.exchange_base import ExchangeBase
from hummingbot.strategy.cross_exchange_market_making.cross_exchange_market_making_config_map import (
    cross_exchange_market_making_config_map as strategy_cmap,
)


class XEMMStartTest(unittest.TestCase):

    def setUp(self) -> None:
        super().setUp()
        self.strategy = None
        self.client_config_map = ClientConfigAdapter(ClientConfigMap())
        self.client_config_map.strategy_report_interval = 60.
        self.markets = {
            "binance": ExchangeBase(client_config_map=self.client_config_map),
            "kucoin": ExchangeBase(client_config_map=self.client_config_map)}
        self.notifications = []
        self.log_errors = []
        assign_config_default(strategy_cmap)
        strategy_cmap.get("maker_market").value = "binance"
        strategy_cmap.get("taker_market").value = "kucoin"
        strategy_cmap.get("maker_market_trading_pair").value = "ETH-USDT"
        strategy_cmap.get("taker_market_trading_pair").value = "ETH-USDT"
        strategy_cmap.get("order_amount").value = Decimal("1")
        strategy_cmap.get("min_profitability").value = Decimal("2")
        strategy_cmap.get("use_oracle_conversion_rate").value = False

    def _initialize_market_assets(self, market, trading_pairs):
        return [("ETH", "USDT")]

    def _initialize_markets(self, market_names):
        pass

    def _notify(self, message):
        self.notifications.append(message)

    def logger(self):
        return self

    def error(self, message, exc_info):
        self.log_errors.append(message)

    def test_strategy_creation(self):
        strategy_start.start(self)
        self.assertEqual(self.strategy.order_amount, Decimal("1"))
        self.assertEqual(self.strategy.min_profitability, Decimal("0.02"))
