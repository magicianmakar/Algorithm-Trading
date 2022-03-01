# you need to install to programs: curl and envsubst

# You must the following values in your command line
# GATEWAY_CERT and GATEWAY_KEY are file paths that should match
# the cert files in the same place as CERT_PATH from /conf/gateway-config.yml

# Here are some examples
# export ETH_PUBLIC_KEY='0x...'
# export ETH_PRIVATE_KEY='...'
# export GATEWAY_CERT='/home/hummingbot/gateway/certs/client_cert.pem'
# export GATEWAY_KEY='/home/hummingbot/gateway/certs/client_key.pem'

# -k is --insecure, this disables certificate verfication and should only be
# used for local development and testing


# test that the gateway-api server is running
curl -s -X GET -k --key $GATEWAY_KEY --cert $GATEWAY_CERT https://localhost:5000/ | jq

## Config

curl -s -X GET -k --key $GATEWAY_KEY --cert $GATEWAY_CERT https://localhost:5000/connectors | jq

curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/config_update.json)" https://localhost:5000/config/update | jq

## Network

curl -s -X GET -k --key $GATEWAY_KEY --cert $GATEWAY_CERT https://localhost:5000/network/status | jq

curl -s -X GET -k --key $GATEWAY_KEY --cert $GATEWAY_CERT https://localhost:5000/network/config | jq

curl -s -X GET -k --key $GATEWAY_KEY --cert $GATEWAY_CERT https://localhost:5000/network/tokens?chain=ethereum&network=kovan | jq

curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/network_balances.json)" https://localhost:5000/network/balances | jq

curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/network_poll.json)" https://localhost:5000/network/poll | jq

# Wallet

# add keys
curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/add_ethereum_key.json)" https://localhost:5000/wallet/add | jq

curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/add_avalanche_key.json)" https://localhost:5000/wallet/add | jq

# read keys
curl -s -X GET -k --key $GATEWAY_KEY --cert $GATEWAY_CERT https://localhost:5000/wallet | jq

# remove keys
curl -s -X DELETE -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/remove_ethereum_key.json)" https://localhost:5000/wallet/remove | jq

curl -s -X DELETE -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/remove_avalanche_key.json)" https://localhost:5000/wallet/remove | jq


# get solana config
curl -s -X GET -k --key $GATEWAY_KEY --cert $GATEWAY_CERT https://localhost:5000/solana | jq

# 0x2b5ad5c4795c026514f8317c7a215e218dccd6cf







curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/balances_0x14.json)" https://localhost:5000/network/balances | jq
curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/balances_0x82.json)" https://localhost:5000/network/balances | jq

curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/nonce_0x14.json)" https://localhost:5000/evm/nonce | jq
curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/nonce_0x82.json)" https://localhost:5000/evm/nonce | jq

curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/allowances_0x14.json)" https://localhost:5000/evm/allowances | jq
curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/allowances_0x82.json)" https://localhost:5000/evm/allowances | jq

curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/approve_0x14.json)" https://localhost:5000/evm/approve | jq
curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/approve_0x82.json)" https://localhost:5000/evm/approve | jq


curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/price_uniswap.json)" https://localhost:5000/trading/price | jq








# get Ethereum allowances for uniswap on an address
curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/eth_allowances.json)" https://localhost:5000/eth/allowances | jq

# approve uniswap allowance on an address
curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/eth_approve.json)" https://localhost:5000/eth/approve | jq

# approve uniswap allowance on an address
curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/eth_approve_with_fees.json)" https://localhost:5000/eth/approve | jq

# remove uniswap allowance on an address
curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/eth_remove_allowance.json)" https://localhost:5000/eth/approve | jq

# get the next nonce you should use for an address
curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/eth_nonce.json)" https://localhost:5000/eth/nonce | jq

# call approve with a nonce, if the nonce is incorrect, this should fail
curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/eth_approve_with_nonce.json)" https://localhost:5000/eth/approve | jq

# poll the status of an ethereum transaction
curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/eth_poll.json)" https://localhost:5000/eth/poll | jq

# cancel a transaction. Note: modify to send the nonce of the transaction to be canceled
curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/eth_cancel.json)" https://localhost:5000/eth/cancel | jq


# TEST Uniswap

# get the price of a trade
curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/eth_uniswap_price.json)" https://localhost:5000/eth/uniswap/price | jq

# perform a trade
curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/eth_uniswap_trade.json)" https://localhost:5000/eth/uniswap/trade | jq

# perform a trade with custom fees
curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/eth_uniswap_trade_with_fees.json)" https://localhost:5000/eth/uniswap/trade | jq



# TEST Avalanche

# get the next nonce you should use for an address
curl -s -X POST -k --key $GATEWAY_KEY --cert $GATEWAY_CERT -H "Content-Type: application/json" -d "$(envsubst < ./requests/avalanche_nonce.json)" https://localhost:5000/avalanche/nonce | jq
