#!/usr/bin/env python

connector_status = {
    'altmarkets': 'bronze',
    'ascend_ex': 'silver',
    'binance': 'gold',
    'binance_perpetual': 'gold',
    'binance_perpetual_testnet': 'gold',
    'binance_us': 'bronze',
    'bitfinex': 'bronze',
    'bitget_perpetual': 'bronze',
    'bitmart': 'bronze',
    'bittrex': 'bronze',
    'bitmex': 'bronze',
    'bitmex_perpetual': 'bronze',
    'bitmex_testnet': 'bronze',
    'bitmex_perpetual_testnet': 'bronze',
    'bybit_perpetual': 'bronze',
    'bybit_perpetual_testnet': 'bronze',
    'bybit_testnet': 'bronze',
    'bybit': 'bronze',
    'coinbase_pro': 'bronze',
    'crypto_com': 'bronze',
    'dydx_perpetual': 'silver',
    'gate_io': 'silver',
    'gate_io_perpetual': 'silver',
    'hitbtc': 'bronze',
    'huobi': 'bronze',
    'k2': 'bronze',
    'kraken': 'bronze',
    'kucoin': 'silver',
    'kucoin_testnet': 'silver',
    'lbank': 'bronze',
    'loopring': 'bronze',
    'mexc': 'bronze',
    'ndax': 'bronze',
    'ndax_testnet': 'bronze',
    'okx': 'bronze',
    'perpetual_finance': 'bronze',
    'probit': 'bronze',
    'whitebit': 'bronze',
    'ciex': 'bronze',
    'uniswap': 'gold',
    'uniswapLP': 'gold',
    'pancakeswap': 'silver',
    'sushiswap': 'silver',
    'traderjoe': 'bronze',
    'quickswap': 'bronze',
    'perp': 'bronze',
    'openocean': 'bronze',
    'pangolin': 'bronze',
    'defikingdoms': 'bronze',
    'defira': 'bronze',
    'mad_meerkat': 'bronze',
    'vvs': 'bronze',
    'ref': 'bronze',
}

warning_messages = {
}


def get_connector_status(connector_name: str) -> str:
    """
    Indicator whether a connector is working properly or not.
    UNKNOWN means the connector is not in connector_status dict.
    RED means a connector doesn't work.
    YELLOW means the connector is either new or has one or more issues.
    GREEN means a connector is working properly.
    """
    if connector_name not in connector_status.keys():
        status = "UNKNOWN"
    else:
        return f"&c{connector_status[connector_name].upper()}"
    return status
