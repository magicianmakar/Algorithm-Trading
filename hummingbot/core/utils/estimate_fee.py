from decimal import Decimal

from hummingbot.core.data_type.trade_fee import TradeFeePercentageApplication, TradeFeeSchema
from hummingbot.core.event.events import OrderType, TradeFee, TradeType, PositionAction
from hummingbot.client.config.fee_overrides_config_map import fee_overrides_config_map
from hummingbot.client.settings import AllConnectorSettings


def build_trade_fee(
    exchange: str,
    is_maker: bool,
    base_currency: str,
    quote_currency: str,
    order_type: OrderType,
    order_side: TradeType,
    amount: Decimal,
    price: Decimal = Decimal("NaN"),
) -> TradeFee:
    """
    Uses the exchange's `TradeFeeSchema` to build a `TradeFee`, given the trade parameters.
    """
    if exchange not in AllConnectorSettings.get_connector_settings():
        raise Exception(f"Invalid connector. {exchange} does not exist in AllConnectorSettings")
    trade_fee_schema = AllConnectorSettings.get_connector_settings()[exchange].trade_fee_schema
    trade_fee_schema = _superimpose_overrides(exchange, trade_fee_schema)
    percent = trade_fee_schema.maker_percent_fee_decimal if is_maker else trade_fee_schema.taker_percent_fee_decimal
    percentage_application = (
        TradeFeePercentageApplication.AddedToCost
        if order_side == TradeType.BUY or trade_fee_schema.percent_fee_token is not None
        else TradeFeePercentageApplication.DeductedFromReturns
    )
    fixed_fees = trade_fee_schema.maker_fixed_fees if is_maker else trade_fee_schema.taker_fixed_fees
    trade_fee = TradeFee(percent, trade_fee_schema.percent_fee_token, percentage_application, fixed_fees)
    return trade_fee


def build_perpetual_trade_fee(
    exchange: str,
    is_maker: bool,
    position_action: PositionAction,
    base_currency: str,
    quote_currency: str,
    order_type: OrderType,
    order_side: TradeType,
    amount: Decimal,
    price: Decimal = Decimal("NaN"),
) -> TradeFee:
    """
    Uses the exchange's `TradeFeeSchema` to build a `TradeFee`, given the trade parameters.
    """
    if exchange not in AllConnectorSettings.get_connector_settings():
        raise Exception(f"Invalid connector. {exchange} does not exist in AllConnectorSettings")
    trade_fee_schema = AllConnectorSettings.get_connector_settings()[exchange].trade_fee_schema
    trade_fee_schema = _superimpose_overrides(exchange, trade_fee_schema)
    percent = trade_fee_schema.maker_percent_fee_decimal if is_maker else trade_fee_schema.taker_percent_fee_decimal
    percentage_application = (
        TradeFeePercentageApplication.AddedToCost
        if position_action == PositionAction.OPEN or trade_fee_schema.percent_fee_token is not None
        else TradeFeePercentageApplication.DeductedFromReturns
    )
    fixed_fees = trade_fee_schema.maker_fixed_fees if is_maker else trade_fee_schema.taker_fixed_fees
    trade_fee = TradeFee(percent, trade_fee_schema.percent_fee_token, percentage_application, fixed_fees)
    return trade_fee


def _superimpose_overrides(exchange: str, trade_fee_schema: TradeFeeSchema):
    trade_fee_schema.percent_fee_token = (
        fee_overrides_config_map.get(f"{exchange}_percent_fee_token")
        or trade_fee_schema.percent_fee_token
    )
    trade_fee_schema.maker_percent_fee_decimal = (
        fee_overrides_config_map.get(f"{exchange}_maker_percent_fee") / Decimal("100")
        if fee_overrides_config_map.get(f"{exchange}_maker_percent_fee") is not None
        else trade_fee_schema.maker_percent_fee_decimal
    )
    trade_fee_schema.taker_percent_fee_decimal = (
        fee_overrides_config_map.get(f"{exchange}_taker_percent_fee") / Decimal("100")
        if fee_overrides_config_map.get(f"{exchange}_taker_percent_fee") is not None
        else trade_fee_schema.taker_percent_fee_decimal
    )
    trade_fee_schema.buy_percent_fee_deducted_from_returns = (
        fee_overrides_config_map.get(f"{exchange}_buy_percent_fee_deducted_from_returns")
        or trade_fee_schema.buy_percent_fee_deducted_from_returns
    )
    trade_fee_schema.maker_fixed_fees = (
        fee_overrides_config_map.get(f"{exchange}_maker_fixed_fees")
        or trade_fee_schema.maker_fixed_fees
    )
    trade_fee_schema.taker_fixed_fees = (
        fee_overrides_config_map.get(f"{exchange}_taker_fixed_fees")
        or trade_fee_schema.taker_fixed_fees
    )
    trade_fee_schema.validate_schema()
    return trade_fee_schema


def estimate_fee(exchange: str, is_maker: bool) -> TradeFee:
    """
    !WARNING!: This method is deprecated and remains only for backward compatibility.
    Use `build_trade_fee` and `build_perpetual_trade_fee` instead.

    Estimate the fee of a transaction on any blockchain.
    exchange is the name of the exchange to query.
    is_maker if true look at fee from maker side, otherwise from taker side.
    """
    trade_fee = build_trade_fee(
        exchange,
        is_maker,
        base_currency="",
        quote_currency="",
        order_type=OrderType.LIMIT,
        order_side=TradeType.BUY,
        amount=Decimal("0"),
        price=Decimal("0"),
    )
    return trade_fee
