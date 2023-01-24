![Hummingbot](https://i.ibb.co/X5zNkKw/blacklogo-with-text.png)

----
[![License](https://img.shields.io/badge/License-Apache%202.0-informational.svg)](https://github.com/hummingbot/hummingbot/blob/master/LICENSE)
[![Twitter](https://img.shields.io/twitter/url?url=https://twitter.com/_hummingbot?style=social&label=_hummingbot)](https://twitter.com/_hummingbot)
[![Youtube](https://img.shields.io/youtube/channel/subscribers/UCxzzdEnDRbylLMWmaMjywOA)](https://www.youtube.com/@hummingbot)
[![Discord](https://img.shields.io/discord/530578568154054663?logo=discord&logoColor=white&style=flat-square)](https://discord.gg/hummingbot/)

Hummingbot is an open source  framework that helps you build automated trading strategies, or **bots** that run on cryptocurrency exchanges.

This code is free and publicly available under the Apache 2.0 open source license!

## Why Hummingbot?

* **Both CEX and DEX connectors**: Hummingbot supports connectors to centralized exchanges like Binance and KuCoin, as well as decentralized exchanges like Uniswap and PancakeSwap on various blockchains (Ethereum, BNB Chain, etc).
* **Community-contributed strategies**: The Hummingbot community has added many customizable templates for market making, arbitrage, and other algo trading strategies.
* **Secure local client**: Hummingbot is a local client software that you install and run on your own devices or cloud virtual machines. It encrypts your API keys and private keys and never exposes them to any third parties.
* **Community modules and events**: Hummingbot is driven by a global community of quant traders and developers. Check out community-maintained modules like Orchestration, join our bi-weekly developer calls, and learn how to build custom strategies using Hummingbot by taking Botcamp!

Help us **democratize high-frequency trading** and make powerful trading algorithms accessible to everyone in the world!


## Quick Links

* [Docs](https://docs.hummingbot.org): Check out the official Hummingbot documentation
* [Installation](https://hummingbot.org/installation/): Install Hummingbot on various platforms
* [FAQs](https://hummingbot.org/faq/): Answers to all your burning questions
* [Botcamp](https://hummingbot.org/botcamp/): Learn how build your own custom HFT strategy in Hummingbot with our hands-on bootcamp!
* [HBOT](https://hummingbot.org/hbot/): Learn how you can decide how this codebase evolves by voting with HBOT tokens 

## Community

* [Newsletter](https://hummingbot.substack.com): Get our monthly newletter whenever we ship a new release
* [Discord](https://discord.gg/hummingbot): The main gathering spot for the global Hummingbot community
* [YouTube](https://www.youtube.com/c/hummingbot): Videos that teach you how to get the most of of Hummingbot
* [Twitter](https://twitter.com/_hummingbot): Get the latest announcements about Hummingbot
* [Snapshot](https://twitter.com/_hummingbot): Participate in monthly polls that decide which components should be prioritized and included

## Exchange Connectors

Hummingbot connectors standardize trading logic and order types across different exchange types. Currently, we support the following exchange types:

 * **SPOT**: Connectors to central limit order book (CLOB) exchanges that trade spot markets
 * **PERP**: Connectors to central limit order book (CLOB) exchanges that trade perpetual swap markets
 * **AMM**: Connectors to decentralized exchanges that use the Automatic Market Maker (AMM) methodology

Exchanges may be centralized (**CEX**), or decentralized (**DEX**), in which case user assets are stored on the blockchain and trading is performed via wallet addresses.

| Tier | Exchange | Type | Signup code |
|------|----------|------|-------------|
| ![](https://img.shields.io/static/v1?label=Hummingbot&message=GOLD&color=yellow) | [Binance](https://www.binance.com/en/register?ref=FQQNNGCD) | SPOT CEX | [FQQNNGCD](https://www.binance.com/en/register?ref=FQQNNGCD)
| ![](https://img.shields.io/static/v1?label=Hummingbot&message=GOLD&color=yellow) | [Binance Futures](https://www.binance.com/en/futures/ref?code=hummingbot) | PERP CEX | [hummingbot](https://www.binance.com/en/futures/ref?code=hummingbot)
| ![](https://img.shields.io/static/v1?label=Hummingbot&message=GOLD&color=yellow) | [Uniswap](https://uniswap.org/) | AMM DEX |
| ![](https://img.shields.io/static/v1?label=Hummingbot&message=SILVER&color=silver) | [KuCoin](https://www.kucoin.com/ucenter/signup?rcode=272KvRf) | SPOT CEX | [272KvRf](https://www.kucoin.com/ucenter/signup?rcode=272KvRf)
| ![](https://img.shields.io/static/v1?label=Hummingbot&message=SILVER&color=silver) | [Gate.io](https://www.gate.io/signup/5868285) | SPOT CEX | [5868285](https://www.gate.io/signup/5868285)
| ![](https://img.shields.io/static/v1?label=Hummingbot&message=SILVER&color=silver) | [AscendEx](https://ascendex.com/register?inviteCode=UEIXNXKW) | SPOT CEX | [UEIXNXKW](https://ascendex.com/register?inviteCode=UEIXNXKW)
| ![](https://img.shields.io/static/v1?label=Hummingbot&message=SILVER&color=silver) | [PancakeSwap](https://pancakeswap.finance/) | AMM DEX |
| ![](https://img.shields.io/static/v1?label=Hummingbot&message=SILVER&color=silver) | [Sushiswap](https://sushi.com/) | AMM DEX |
| ![](https://img.shields.io/static/v1?label=Hummingbot&message=SILVER&color=silver) | [dYdX](https://dydx.exchange/) | PERP DEX |

Quarterly [Polls](https://hummingbot.org/maintenance/certification/) allow the Hummingbot community to vote using HBOT tokens to decide which exchanges should be certified GOLD or SILVER, which means that they are maintained and continually improved by Hummingbot Foundation. In addition, the codebase includes BRONZE exchange connectors that are maintained by community members. See the [Hummingbot documentation](https://docs.hummingbot.org/exchanges) for all exchanges supported.

## Strategies and Scripts

We provide customizable strategy templates for core trading strategies that users can configure, extend, and run. Hummingbot Foundation maintains three **CORE** strategies:

* [Pure Market Making](https://docs.hummingbot.org/strategies/pure-market-making/): Our original single-pair market making strategy
* [Cross Exchange Market Making](https://docs.hummingbot.org/strategies/cross-exchange-market-making/): Provide liquidity while hedging filled orders on another exchange
* [AMM Arbitrage](https://docs.hummingbot.org/strategies/amm-arbitrage/): Exploits price differences between AMM and SPOT exchanges

**CORE** strategies are selected via HBOT voting through quarterly [Polls](https://hummingbot.org/maintenance/certification/). In addition, the codebase includes **COMMUNITY** strategies that are maintained by individuals or firms in the community. See the [Hummingbot documentation](https://docs.hummingbot.org/strategies) for all strategies supported.

### Scripts

Scripts are a newer, lighter way to build Hummingbot strategies in Python, which let you modify the script's code and re-run it to apply the changes without exiting the Hummingbot interface or re-compiling the code.

See the [Scripts](https://docs.hummingbot.org/scripts/) section in the documentation for more info, or check out the [/scripts](https://github.com/hummingbot/hummingbot/tree/master/scripts) folder for all Script examples included in the codebase.

## Other Hummingbot Repos

* [Hummingbot Site](https://github.com/hummingbot/hummingbot-site): Official documentation for Hummingbot - we welcome contributions here too!
* [Hummingbot Project Management](https://github.com/hummingbot/pm): Agendas and recordings of regular Hummingbot developer and community calls
* [Awesome Hummingbot](https://github.com/hummingbot/awesome-hummingbot): All the Hummingbot links
* [Hummingbot StreamLit Apps](https://github.com/hummingbot/streamlit-apps): Hummingbot-related StreamLit data apps and dashboards
* [Community Tools](https://github.com/hummingbot/community-tools): Community contributed resources related to Hummingbot
* [Brokers](https://github.com/hummingbot/brokers): Different brokers that can be used to communicate with multiple instances of Hummingbot

## Contributions

Hummingbot belongs to its community, so we welcome contributions! Please review these [guidelines](./CONTRIBUTING.md) first.

To have your pull request merged into the codebase, submit a [Pull Request Proposal](https://snapshot.org/#/hbot-prp.eth) on our Snapshot. Note that you will need 1 HBOT in your Ethereum wallet to submit a Pull Request Proposal. See [HBOT](https://hummingbot.org/hbot) for more information.

## Legal

* **License**: Hummingbot is licensed under [Apache 2.0](./LICENSE).
* **Data collection**: read important information regarding [Hummingbot Data Collection](./DATA_COLLECTION.md).
