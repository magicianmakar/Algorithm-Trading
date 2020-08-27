#!/usr/bin/env python

import sys
import asyncio
import logging
import unittest
import conf

from os.path import join, realpath
from typing import (
    Optional
)
from hummingbot.market.crypto_com.crypto_com_user_stream_tracker import CryptoComUserStreamTracker
from hummingbot.market.crypto_com.crypto_com_auth import CryptoComAuth
from hummingbot.core.utils.async_utils import safe_ensure_future

sys.path.insert(0, realpath(join(__file__, "../../../")))


class CryptoComUserStreamTrackerUnitTest(unittest.TestCase):
    user_stream_tracker: Optional[CryptoComUserStreamTracker] = None

    @classmethod
    def setUpClass(cls):
        cls.ev_loop: asyncio.BaseEventLoop = asyncio.get_event_loop()
        cls.crypto_com_auth = CryptoComAuth(conf.crypto_com_api_key, conf.crypto_com_secret_key)
        cls.trading_pairs = ["BTC_USDT"]
        cls.user_stream_tracker: CryptoComUserStreamTracker = CryptoComUserStreamTracker(
            crypto_com_auth=cls.crypto_com_auth, trading_pairs=cls.trading_pairs)
        cls.user_stream_tracker_task: asyncio.Task = safe_ensure_future(cls.user_stream_tracker.start())

    def test_user_stream(self):
        # Wait process some msgs.
        self.ev_loop.run_until_complete(asyncio.sleep(120.0))
        print(self.user_stream_tracker.user_stream)


def main():
    logging.basicConfig(level=logging.INFO)
    unittest.main()


if __name__ == "__main__":
    main()
