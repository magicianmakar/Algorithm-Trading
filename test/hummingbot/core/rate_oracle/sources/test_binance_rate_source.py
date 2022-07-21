import asyncio
import json
import unittest
from decimal import Decimal
from typing import Awaitable

from aioresponses import aioresponses

from hummingbot.connector.exchange.binance import binance_constants as CONSTANTS, binance_web_utils as web_utils
from hummingbot.connector.utils import combine_to_hb_trading_pair
from hummingbot.core.rate_oracle.sources.binance_rate_source import BinanceRateSource


class BinanceRateSourceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.ev_loop = asyncio.get_event_loop()
        cls.target_token = "COINALPHA"
        cls.global_token = "HBOT"
        cls.binance_pair = f"{cls.target_token}{cls.global_token}"
        cls.trading_pair = combine_to_hb_trading_pair(base=cls.target_token, quote=cls.global_token)
        cls.binance_us_pair = f"{cls.target_token}USD"
        cls.us_trading_pair = combine_to_hb_trading_pair(base=cls.target_token, quote="USD")
        cls.binance_ignored_pair = "SOMEPAIR"
        cls.ignored_trading_pair = combine_to_hb_trading_pair(base="SOME", quote="PAIR")

    def async_run_with_timeout(self, coroutine: Awaitable, timeout: int = 1):
        ret = asyncio.get_event_loop().run_until_complete(asyncio.wait_for(coroutine, timeout))
        return ret

    def setup_binance_responses(self, mock_api, expected_rate: Decimal):
        pairs_us_url = web_utils.public_rest_url(path_url=CONSTANTS.EXCHANGE_INFO_PATH_URL, domain="us")
        pairs_url = web_utils.public_rest_url(path_url=CONSTANTS.EXCHANGE_INFO_PATH_URL)
        symbols_response = {  # truncated
            "symbols": [
                {
                    "symbol": self.binance_pair,
                    "status": "TRADING",
                    "baseAsset": self.target_token,
                    "quoteAsset": self.global_token,
                    "permissions": [
                        "SPOT",
                    ],
                },
                {
                    "symbol": self.binance_us_pair,
                    "status": "TRADING",
                    "baseAsset": self.target_token,
                    "quoteAsset": "USD",
                    "permissions": [
                        "SPOT",
                    ],
                },
                {
                    "symbol": self.binance_ignored_pair,
                    "status": "PAUSED",
                    "baseAsset": "SOME",
                    "quoteAsset": "PAIR",
                    "permissions": [
                        "SPOT",
                    ],
                },
            ]
        }
        binance_prices_us_url = web_utils.public_rest_url(path_url=CONSTANTS.TICKER_BOOK_PATH_URL, domain="us")
        binance_prices_us_response = [
            {
                "symbol": self.binance_us_pair,
                "bidPrice": "20862.0000",
                "bidQty": "0.50000000",
                "askPrice": "20865.6100",
                "askQty": "0.14500000",
            },
            {
                "symbol": self.binance_ignored_pair,
                "bidPrice": "0",
                "bidQty": "0",
                "askPrice": "0",
                "askQty": "0",
            }
        ]
        binance_prices_global_url = web_utils.public_rest_url(path_url=CONSTANTS.TICKER_BOOK_PATH_URL)
        binance_prices_global_response = [
            {
                "symbol": self.binance_pair,
                "bidPrice": str(expected_rate - Decimal("0.1")),
                "bidQty": "0.50000000",
                "askPrice": str(expected_rate + Decimal("0.1")),
                "askQty": "0.14500000",
            }
        ]
        mock_api.get(pairs_us_url, body=json.dumps(symbols_response))
        mock_api.get(pairs_url, body=json.dumps(symbols_response))
        mock_api.get(binance_prices_us_url, body=json.dumps(binance_prices_us_response))
        mock_api.get(binance_prices_global_url, body=json.dumps(binance_prices_global_response))

    @aioresponses()
    def test_get_binance_prices(self, mock_api):
        expected_rate = Decimal("10")
        self.setup_binance_responses(mock_api=mock_api, expected_rate=expected_rate)

        rate_source = BinanceRateSource()
        prices = self.async_run_with_timeout(rate_source.get_prices())

        self.assertIn(self.trading_pair, prices)
        self.assertEqual(expected_rate, prices[self.trading_pair])
        self.assertIn(self.us_trading_pair, prices)
        self.assertNotIn(self.ignored_trading_pair, prices)
