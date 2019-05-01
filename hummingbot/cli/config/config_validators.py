from os.path import (
    isfile,
    join,
)
from hummingbot.cli.settings import (
    EXCHANGES,
    STRATEGIES,
    CONF_FILE_PATH,
    symbol_fetcher,
)


# Validators
def is_exchange(value: str) -> bool:
    return value in EXCHANGES


def is_strategy(value: str) -> bool:
    return value in STRATEGIES


def is_path(value: str) -> bool:
    return isfile(join(CONF_FILE_PATH, value)) and value.endswith('.yml')


def is_valid_market_symbol(market: str, value: str) -> bool:
    if symbol_fetcher.ready:
        market_symbols = symbol_fetcher.symbols.get(market, [])
        return value in symbol_fetcher.symbols.get(market) if len(market_symbols) > 0 else True


