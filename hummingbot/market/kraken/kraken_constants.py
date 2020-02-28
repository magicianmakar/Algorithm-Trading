CRYPTO_QUOTES = [
    "XXBT",
    "XETH",
    "USDT",
    "DAI",
    "USDC",
]

BASE_ORDER_MIN = {
    "ALGO": 50,
    "XREP": 0.3,
    "BAT": 50,
    "XXBT": 0.002,
    "BCH": 0.000002,
    "ADA": 1,
    "LINK": 10,
    "ATOM": 1,
    "DAI": 10,
    "DASH": 0.03,
    "XXDG": 3000,
    "EOS": 3,
    "XETH": 0.02,
    "XETC": 0.3,
    "GNO": 0.02,
    "ICX": 50,
    "LSK": 10,
    "XLTC": 0.1,
    "XXMR": 0.1,
    "NANO": 10,
    "OMG": 10,
    "PAXG": 0.01,
    "QTUM": 0.1,
    "XXRP": 30,
    "SC": 5000,
    "XXLM": 30,
    "USDT": 5,
    "XTZ": 1,
    "USDC": 5,
    "XMLN": 0.1,
    "WAVES": 10,
    "XZEC": 0.03,
}

HB_PAIR_TO_KRAKEN_PAIR = {
    'ADA-XETH': 'ADAETH',
    'ADA-ZEUR': 'ADAEUR',
    'ADA-ZUSD': 'ADAUSD',
    'ADA-XXBT': 'ADAXBT',
    'ALGO-XETH': 'ALGOETH',
    'ALGO-ZEUR': 'ALGOEUR',
    'ALGO-ZUSD': 'ALGOUSD',
    'ALGO-XXBT': 'ALGOXBT',
    'ATOM-XETH': 'ATOMETH',
    'ATOM-ZEUR': 'ATOMEUR',
    'ATOM-ZUSD': 'ATOMUSD',
    'ATOM-XXBT': 'ATOMXBT',
    'BAT-XETH': 'BATETH',
    'BAT-ZEUR': 'BATEUR',
    'BAT-ZUSD': 'BATUSD',
    'BAT-XXBT': 'BATXBT',
    'BCH-ZEUR': 'BCHEUR',
    'BCH-ZUSD': 'BCHUSD',
    'BCH-XXBT': 'BCHXBT',
    'DAI-ZEUR': 'DAIEUR',
    'DAI-ZUSD': 'DAIUSD',
    'DAI-USDT': 'DAIUSDT',
    'DASH-ZEUR': 'DASHEUR',
    'DASH-ZUSD': 'DASHUSD',
    'DASH-XXBT': 'DASHXBT',
    'EOS-XETH': 'EOSETH',
    'EOS-ZEUR': 'EOSEUR',
    'EOS-ZUSD': 'EOSUSD',
    'EOS-XXBT': 'EOSXBT',
    'XETH-CHF': 'ETHCHF',
    'XETH-DAI': 'ETHDAI',
    'XETH-USDC': 'ETHUSDC',
    'XETH-USDT': 'ETHUSDT',
    'GNO-XETH': 'GNOETH',
    'GNO-ZEUR': 'GNOEUR',
    'GNO-ZUSD': 'GNOUSD',
    'GNO-XXBT': 'GNOXBT',
    'ICX-XETH': 'ICXETH',
    'ICX-ZEUR': 'ICXEUR',
    'ICX-ZUSD': 'ICXUSD',
    'ICX-XXBT': 'ICXXBT',
    'LINK-XETH': 'LINKETH',
    'LINK-ZEUR': 'LINKEUR',
    'LINK-ZUSD': 'LINKUSD',
    'LINK-XXBT': 'LINKXBT',
    'LSK-XETH': 'LSKETH',
    'LSK-ZEUR': 'LSKEUR',
    'LSK-ZUSD': 'LSKUSD',
    'LSK-XXBT': 'LSKXBT',
    'NANO-XETH': 'NANOETH',
    'NANO-ZEUR': 'NANOEUR',
    'NANO-ZUSD': 'NANOUSD',
    'NANO-XXBT': 'NANOXBT',
    'OMG-XETH': 'OMGETH',
    'OMG-ZEUR': 'OMGEUR',
    'OMG-ZUSD': 'OMGUSD',
    'OMG-XXBT': 'OMGXBT',
    'PAXG-XETH': 'PAXGETH',
    'PAXG-ZEUR': 'PAXGEUR',
    'PAXG-ZUSD': 'PAXGUSD',
    'PAXG-XXBT': 'PAXGXBT',
    'QTUM-XETH': 'QTUMETH',
    'QTUM-ZEUR': 'QTUMEUR',
    'QTUM-ZUSD': 'QTUMUSD',
    'QTUM-XXBT': 'QTUMXBT',
    'SC-XETH': 'SCETH',
    'SC-ZEUR': 'SCEUR',
    'SC-ZUSD': 'SCUSD',
    'SC-XXBT': 'SCXBT',
    'USDC-ZEUR': 'USDCEUR',
    'USDC-ZUSD': 'USDCUSD',
    'USDC-USDT': 'USDCUSDT',
    'USDT-ZCAD': 'USDTCAD',
    'USDT-ZEUR': 'USDTEUR',
    'USDT-ZGBP': 'USDTGBP',
    'USDT-ZUSD': 'USDTZUSD',
    'WAVES-XETH': 'WAVESETH',
    'WAVES-ZEUR': 'WAVESEUR',
    'WAVES-ZUSD': 'WAVESUSD',
    'WAVES-XXBT': 'WAVESXBT',
    'XXBT-CHF': 'XBTCHF',
    'XXBT-DAI': 'XBTDAI',
    'XXBT-USDC': 'XBTUSDC',
    'XXBT-USDT': 'XBTUSDT',
    'XXDG-ZEUR': 'XDGEUR',
    'XXDG-ZUSD': 'XDGUSD',
    'XETC-XETH': 'XETCXETH',
    'XETC-XXBT': 'XETCXXBT',
    'XETC-ZEUR': 'XETCZEUR',
    'XETC-ZUSD': 'XETCZUSD',
    'XETH-XXBT': 'XETHXXBT',
    'XETH-ZCAD': 'XETHZCAD',
    'XETH-ZEUR': 'XETHZEUR',
    'XETH-ZGBP': 'XETHZGBP',
    'XETH-ZJPY': 'XETHZJPY',
    'XETH-ZUSD': 'XETHZUSD',
    'XLTC-XXBT': 'XLTCXXBT',
    'XLTC-ZEUR': 'XLTCZEUR',
    'XLTC-ZUSD': 'XLTCZUSD',
    'XMLN-XETH': 'XMLNXETH',
    'XMLN-XXBT': 'XMLNXXBT',
    'XMLN-ZEUR': 'XMLNZEUR',
    'XMLN-ZUSD': 'XMLNZUSD',
    'XREP-XETH': 'XREPXETH',
    'XREP-XXBT': 'XREPXXBT',
    'XREP-ZEUR': 'XREPZEUR',
    'XREP-ZUSD': 'XREPZUSD',
    'XTZ-XETH': 'XTZETH',
    'XTZ-ZEUR': 'XTZEUR',
    'XTZ-ZUSD': 'XTZUSD',
    'XTZ-XXBT': 'XTZXBT',
    'XXBT-ZCAD': 'XXBTZCAD',
    'XXBT-ZEUR': 'XXBTZEUR',
    'XXBT-ZGBP': 'XXBTZGBP',
    'XXBT-ZJPY': 'XXBTZJPY',
    'XXBT-ZUSD': 'XXBTZUSD',
    'XXDG-XXBT': 'XXDGXXBT',
    'XXLM-XXBT': 'XXLMXXBT',
    'XXLM-ZEUR': 'XXLMZEUR',
    'XXLM-ZUSD': 'XXLMZUSD',
    'XXMR-XXBT': 'XXMRXXBT',
    'XXMR-ZEUR': 'XXMRZEUR',
    'XXMR-ZUSD': 'XXMRZUSD',
    'XXRP-XXBT': 'XXRPXXBT',
    'XXRP-ZCAD': 'XXRPZCAD',
    'XXRP-ZEUR': 'XXRPZEUR',
    'XXRP-ZJPY': 'XXRPZJPY',
    'XXRP-ZUSD': 'XXRPZUSD',
    'XZEC-XXBT': 'XZECXXBT',
    'XZEC-ZEUR': 'XZECZEUR',
    'XZEC-ZUSD': 'XZECZUSD',
}
