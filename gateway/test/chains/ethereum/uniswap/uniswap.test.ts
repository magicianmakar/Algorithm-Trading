jest.useFakeTimers();
import { Uniswap } from '../../../../src/connectors/uniswap/uniswap';
import { patch, unpatch } from '../../../services/patch';
import { UniswapishPriceError } from '../../../../src/services/error-handler';
import { CurrencyAmount, TradeType, Token } from '@uniswap/sdk-core';
import { Pair, Route } from '@uniswap/v2-sdk';
import { Trade } from '@uniswap/router-sdk';
import { BigNumber, utils } from 'ethers';
import { Ethereum } from '../../../../src/chains/ethereum/ethereum';

let ethereum: Ethereum;
let uniswap: Uniswap;

const WETH = new Token(
  3,
  '0xd0A1E359811322d97991E03f863a0C30C2cF029C',
  18,
  'WETH'
);
const DAI = new Token(
  3,
  '0x4f96fe3b7a6cf9725f59d353f723c1bdb64ca6aa',
  18,
  'DAI'
);

beforeAll(async () => {
  ethereum = Ethereum.getInstance('kovan');
  await ethereum.init();
  uniswap = Uniswap.getInstance('ethereum', 'kovan');
  await uniswap.init();
});

afterEach(() => {
  unpatch();
});

const patchTrade = (key: string, error?: Error) => {
  patch(uniswap.alphaRouter.route, key, () => {
    if (error) return [];
    const WETH_DAI = new Pair(
      CurrencyAmount.fromRawAmount(WETH, '2000000000000000000'),
      CurrencyAmount.fromRawAmount(DAI, '1000000000000000000')
    );
    const DAI_TO_WETH = new Route([WETH_DAI], DAI, WETH);
    return {
      quote: CurrencyAmount.fromRawAmount(DAI, '1000000000000000000'),
      quoteGasAdjusted: CurrencyAmount.fromRawAmount(
        DAI,
        '1000000000000000000'
      ),
      estimatedGasUsed: utils.parseEther('100'),
      estimatedGasUsedQuoteToken: CurrencyAmount.fromRawAmount(
        DAI,
        '1000000000000000000'
      ),
      estimatedGasUsedUSD: CurrencyAmount.fromRawAmount(
        DAI,
        '1000000000000000000'
      ),
      gasPriceWei: utils.parseEther('100'),
      trade: new Trade({
        v2Routes: [
          {
            routev2: DAI_TO_WETH,
            inputAmount: CurrencyAmount.fromRawAmount(
              DAI,
              '1000000000000000000'
            ),
            outputAmount: CurrencyAmount.fromRawAmount(
              WETH,
              '2000000000000000000'
            ),
          },
        ],
        v3Routes: [],
        tradeType: TradeType.EXACT_INPUT,
      }),
      route: [],
      blockNumber: BigNumber.from(5000),
    };
  });
};

describe('verify Uniswap estimateSellTrade', () => {
  it('Should return an ExpectedTrade when available', async () => {
    patchTrade('bestTradeExactIn');

    const expectedTrade = await uniswap.estimateSellTrade(
      WETH,
      DAI,
      BigNumber.from(1)
    );
    expect(expectedTrade).toHaveProperty('trade');
    expect(expectedTrade).toHaveProperty('expectedAmount');
  });

  it('Should throw an error if no pair is available', async () => {
    patchTrade('bestTradeExactIn', new Error('error getting trade'));

    await expect(async () => {
      await uniswap.estimateSellTrade(WETH, DAI, BigNumber.from(1));
    }).rejects.toThrow(UniswapishPriceError);
  });
});

describe('verify Uniswap estimateBuyTrade', () => {
  it('Should return an ExpectedTrade when available', async () => {
    patchTrade('bestTradeExactOut');

    const expectedTrade = await uniswap.estimateBuyTrade(
      WETH,
      DAI,
      BigNumber.from(1)
    );
    expect(expectedTrade).toHaveProperty('trade');
    expect(expectedTrade).toHaveProperty('expectedAmount');
  });

  it('Should return an error if no pair is available', async () => {
    patchTrade('bestTradeExactOut', new Error('error getting trade'));

    await expect(async () => {
      await uniswap.estimateBuyTrade(WETH, DAI, BigNumber.from(1));
    }).rejects.toThrow(UniswapishPriceError);
  });
});
