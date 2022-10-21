from decimal import Decimal

from pydantic import Field, SecretStr

from hummingbot.client.config.config_data_types import BaseConnectorConfigMap, ClientFieldData
from hummingbot.core.data_type.trade_fee import TradeFeeSchema

# Bitget fees: https://www.bitget.com/en/rate?tab=1
DEFAULT_FEES = TradeFeeSchema(
    maker_percent_fee_decimal=Decimal("0.0002"),
    taker_percent_fee_decimal=Decimal("0.0006"),
)

CENTRALIZED = True

EXAMPLE_PAIR = "BTC-USDT"


class BitgetPerpetualConfigMap(BaseConnectorConfigMap):
    connector: str = Field(default="bitget_perpetual", client_data=None)
    bitget_perpetual_api_key: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Bitget Perpetual API key",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        )
    )
    bitget_perpetual_secret_key: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Bitget Perpetual secret key",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        )
    )
    bitget_perpetual_passphrase: SecretStr = Field(
        default=...,
        client_data=ClientFieldData(
            prompt=lambda cm: "Enter your Bitget Perpetual passphrase",
            is_secure=True,
            is_connect_key=True,
            prompt_on_new=True,
        )
    )

    class Config:
        title = "bitget_perpetual"


KEYS = BitgetPerpetualConfigMap.construct()
