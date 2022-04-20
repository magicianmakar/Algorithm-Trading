// @ts-nocheck

import 'jest-extended';
import {Serum} from '../../../../src/connectors/serum/serum';
import {unpatch} from '../../../services/patch';
import {Solana} from '../../../../src/chains/solana/solana';
import {default as config} from './fixtures/serumConfig';
import {createOrders, getMarkets, getOrderBooks, getTickers} from "../../../../src/clob/clob.controllers";
import {getNewOrderTemplate} from "./fixtures/dummy";
import {addWallet} from "../../../../src/services/wallet/wallet.controllers";
import {getOrCreateTokenAccount} from "../../../../src/chains/solana/solana.controllers";

export const publicKey = '3xgEFpNpz1hPU7iHN9P3WPgLTWfZXu6wSUuGw8kigNQr';
export const privateKey =
  '5K23ZvkHuNoakyMKGNoaCvky6a2Yu5yfeoRz2wQLKYAczMKzACN5ZZb9ixu6QcsQvrvh91CNfqu8U1LqC1nvnyfp';

jest.setTimeout(1000000);

let solana: Solana;
let serum: Serum;

beforeAll(async () => {
  solana = await Solana.getInstance(config.solana.network);

  serum = await Serum.getInstance(config.serum.chain, config.serum.network);
});

afterEach(() => {
  unpatch();
});

it('Temporary', async () => {
  const marketName = 'BTC/USDT';

  const commonParameters = {
    chain: config.serum.chain,
    network: config.serum.network,
    connector: config.serum.connector,
  }

  const wallet = addWallet({
    chain: config.serum.chain,
    network: config.serum.network,
    privateKey: privateKey,
  });
  console.log('wallet/add', JSON.stringify(wallet, null, 2));

  const tokenAccount = await getOrCreateTokenAccount(
    solana,
    {
      address: config.solana.wallet.owner.address,
      token: 'BTC',
    }
  );
  console.log('token', JSON.stringify(tokenAccount, null, 2));


  // const market = (await getMarkets({
  //   ...commonParameters,
  //   name: marketName,
  // })).body;
  // console.log('market', JSON.stringify(market, null, 2));

  // const orderBook = (await getOrderBooks({
  //   ...commonParameters,
  //   marketName,
  // })).body;
  // console.log('orderBook', JSON.stringify(orderBook, null, 2));

  // const ticker = (await getTickers({
  //   ...commonParameters,
  //   marketName,
  // })).body;
  // console.log('ticker', JSON.stringify(ticker, null, 2));

  const order = await createOrders({
    ...commonParameters,
    order: getNewOrderTemplate()
  });
  console.log('order', JSON.stringify(order, null, 2));

  // const orders = await createNewOrders(3);
  // expect(orders).toBeDefined();
});
