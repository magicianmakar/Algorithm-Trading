#!/usr/bin/env python
import logging
from os.path import join, realpath
import sys;sys.path.insert(0, realpath(join(__file__, "../../")))

from wings.logger.struct_logger import METRICS_LOG_LEVEL

import asyncio
from decimal import Decimal
import time
from typing import List
import unittest

import conf
from wings.market_base import OrderType
from wings.coinbase_pro_market import CoinbaseProMarket
from wings.clock import (
    Clock,
    ClockMode
)
from wings.events import (
    MarketEvent,
    BuyOrderCompletedEvent,
    SellOrderCompletedEvent,
    MarketReceivedAssetEvent,
    MarketWithdrawAssetEvent,
    OrderFilledEvent,
    BuyOrderCreatedEvent, SellOrderCreatedEvent)
from wings.mock_wallet import MockWallet
from wings.event_logger import EventLogger


MAINNET_RPC_URL = "http://mainnet-rpc.mainnet:8545"
logging.basicConfig(level=METRICS_LOG_LEVEL)


class CoinbaseProMarketUnitTest(unittest.TestCase):
    events: List[MarketEvent] = [
        MarketEvent.ReceivedAsset,
        MarketEvent.BuyOrderCompleted,
        MarketEvent.SellOrderCompleted,
        MarketEvent.WithdrawAsset,
        MarketEvent.OrderFilled,
        MarketEvent.TransactionFailure,
        MarketEvent.BuyOrderCreated,
        MarketEvent.SellOrderCreated
    ]

    market: CoinbaseProMarket
    market_logger: EventLogger

    @classmethod
    def setUpClass(cls):
        global MAINNET_RPC_URL

        cls.clock: Clock = Clock(ClockMode.REALTIME)
        cls.market: CoinbaseProMarket = CoinbaseProMarket(
            web3_url=MAINNET_RPC_URL,
            coinbase_pro_api_key=conf.coinbase_pro_api_key,
            coinbase_pro_secret_key=conf.coinbase_pro_secret_key,
            coinbase_pro_passphrase=conf.coinbase_pro_passphrase,
            symbols=["ETH-USDC"]
        )
        print("Initializing Coinbase Pro market... this will take about a minute.")
        cls.ev_loop: asyncio.BaseEventLoop = asyncio.get_event_loop()
        cls.clock.add_iterator(cls.market)
        cls.ev_loop.run_until_complete(cls.clock.run_til(time.time() + 1))
        cls.ev_loop.run_until_complete(cls.wait_til_ready())
        print("Ready.")

    @classmethod
    async def wait_til_ready(cls):
        while True:
            if cls.market.ready:
                break
            await asyncio.sleep(1.0)

    def setUp(self):
        self.market_logger = EventLogger()
        for event_tag in self.events:
            self.market.add_listener(event_tag, self.market_logger)

    def tearDown(self):
        for event_tag in self.events:
            self.market.remove_listener(event_tag, self.market_logger)
        self.market_logger = None

    async def run_parallel_async(self, *tasks):
        future: asyncio.Future = asyncio.ensure_future(asyncio.gather(*tasks))
        while not future.done():
            now = time.time()
            next_iteration = now // 1.0 + 1
            await self.clock.run_til(next_iteration)
        return future.result()

    def run_parallel(self, *tasks):
        return self.ev_loop.run_until_complete(self.run_parallel_async(*tasks))

    def test_limit_buy_and_sell(self):
        self.assertGreater(self.market.get_balance("ETH"), 0.1)


if __name__ == "__main__":
    unittest.main()
