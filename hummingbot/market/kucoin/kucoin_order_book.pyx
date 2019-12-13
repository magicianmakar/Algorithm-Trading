#!/usr/bin/env python
import logging
from typing import (
    Dict,
    Optional
)
import ujson

from aiokafka import ConsumerRecord
from sqlalchemy.engine import RowProxy

from hummingbot.logger import HummingbotLogger
from hummingbot.core.event.events import TradeType
from hummingbot.core.data_type.order_book cimport OrderBook
from hummingbot.core.data_type.order_book_message import (
    OrderBookMessage,
    OrderBookMessageType
)

_kob_logger = None


cdef class KucoinOrderBook(OrderBook):
    @classmethod
    def logger(cls) -> HummingbotLogger:
        global _kob_logger
        if _kob_logger is None:
            _kob_logger = logging.getLogger(__name__)
        return _kob_logger

    @classmethod
    def snapshot_message_from_exchange(cls,
                                       msg: Dict[str, any],
                                       timestamp: float,
                                       metadata: Optional[Dict] = None) -> OrderBookMessage:
        if metadata:
            msg.update(metadata)
        return OrderBookMessage(OrderBookMessageType.SNAPSHOT, {
            "symbol": msg["symbol"],
            "update_id": int(msg["data"]["sequence"]),
            "bids": msg["data"]["bids"],
            "asks": msg["data"]["asks"]
        }, timestamp=timestamp)

    @classmethod
    def diff_message_from_exchange(cls,
                                   msg: Dict[str, any],
                                   timestamp: Optional[float] = None,
                                   metadata: Optional[Dict] = None) -> OrderBookMessage:
        if metadata:
            msg.update(metadata)
        return OrderBookMessage(OrderBookMessageType.DIFF, {
            "symbol": msg["data"]["symbol"],
            "update_id": msg["data"]["sequenceEnd"],
            "bids": msg["data"]["changes"]["bids"],
            "asks": msg["data"]["changes"]["asks"]
        }, timestamp=timestamp)

    @classmethod
    def snapshot_message_from_db(cls, record: RowProxy, metadata: Optional[Dict] = None) -> OrderBookMessage:
        ts = record["timestamp"]
        msg = record["json"] if type(record["json"])==dict else ujson.loads(record["json"])
        if metadata:
            msg.update(metadata)
        return OrderBookMessage(OrderBookMessageType.SNAPSHOT, {
            "symbol": msg["symbol"],
            "update_id": int(ts),
            "bids": msg["data"]["bids"],
            "asks": msg["data"]["asks"]
        }, timestamp=record["timestamp"] * 1e-3)

    @classmethod
    def diff_message_from_db(cls, record: RowProxy, metadata: Optional[Dict] = None) -> OrderBookMessage:
        ts = record["timestamp"]
        msg = ujson.loads(record["json"]) # Kucoin json in DB is TEXT
        if metadata:
            msg.update(metadata)
        return OrderBookMessage(OrderBookMessageType.DIFF, {
            "symbol": msg["symbol"],
            "update_id": ts,
            "bids": msg["data"]["bids"],
            "asks": msg["data"]["asks"]
        }, timestamp=record["timestamp"] * 1e-3)

    @classmethod
    def snapshot_message_from_kafka(cls, record: ConsumerRecord, metadata: Optional[Dict] = None) -> OrderBookMessage:
        ts = record.timestamp
        msg = ujson.loads(record.value.decode("utf-8"))
        if metadata:
            msg.update(metadata)
        return OrderBookMessage(OrderBookMessageType.SNAPSHOT, {
            "symbol": msg["symbol"],
            "update_id": ts,
            "bids": msg["data"]["bids"],
            "asks": msg["data"]["asks"]
        }, timestamp=record.timestamp * 1e-3)

    @classmethod
    def diff_message_from_kafka(cls, record: ConsumerRecord, metadata: Optional[Dict] = None) -> OrderBookMessage:
        msg = ujson.loads(record.value.decode("utf-8"))
        if metadata:
            msg.update(metadata)
        return OrderBookMessage(OrderBookMessageType.DIFF, {
            "symbol": msg["symbol"],
            "update_id": record.timestamp,
            "bids": msg["data"]["bids"],
            "asks": msg["data"]["asks"]

        }, timestamp=record.timestamp * 1e-3)

    @classmethod
    def trade_message_from_db(cls, record: RowProxy, metadata: Optional[Dict] = None):
        msg = record["json"]
        if metadata:
            msg.update(metadata)
        return OrderBookMessage(OrderBookMessageType.TRADE, {
            "symbol": msg["symbol"],
            "trade_type": float(TradeType.BUY.value) if msg["side"] == "buy"
                            else float(TradeType.SELL.value),
            "trade_id": msg["tradeId"],
            "update_id": msg["sequence"],
            "price": msg["price"],
            "amount": msg["size"]
        }, timestamp=record.timestamp * 1e-9)

    @classmethod
    def trade_message_from_exchange(cls, msg: Dict[str, any], metadata: Optional[Dict] = None):
        if metadata:
            msg.update(metadata)
        return OrderBookMessage(OrderBookMessageType.TRADE, {
            "symbol": msg["symbol"],
            "trade_type": float(TradeType.BUY.value) if msg["side"] == "buy"
                            else float(TradeType.SELL.value),
            "trade_id": msg["tradeId"],
            "update_id": msg["sequence"],
            "price": msg["price"],
            "amount": msg["size"]
        }, timestamp=(int(msg["time"]) * 1e-9))

    @classmethod
    def from_snapshot(cls, msg: OrderBookMessage) -> "OrderBook":
        retval = KucoinOrderBook()
        retval.apply_snapshot(msg.bids, msg.asks, msg.update_id)
        return retval

