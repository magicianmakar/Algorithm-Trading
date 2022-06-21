import request from 'supertest';
import { gatewayApp } from '../../../../src/app';
import { Avalanche } from '../../../../src/chains/avalanche/avalanche';
import { Openocean } from '../../../../src/connectors/openocean/openocean';
import { patchEVMNonceManager } from '../../../evm.nonce.mock';
let avalanche: Avalanche;
let openocean: Openocean;

const address: string = '0x00000000000000000000000000000000000';
const privateKey =
  '0000000000000000000000000000000000000000000000000000000000000002'; // noqa: mock

beforeAll(async () => {
  avalanche = Avalanche.getInstance('avalanche');
  patchEVMNonceManager(avalanche.nonceManager);
  await avalanche.init();
  openocean = Openocean.getInstance('avalanche', 'avalanche');
  await openocean.init();

  const passphrase = 'waylin_args_passphrase';
  process.argv.push(`--passphrase=${passphrase}`);

  await request(gatewayApp)
    .post(`/wallet/add`)
    .send({
      privateKey: privateKey,
      chain: 'avalanche',
      network: 'avalanche',
    })
    .expect('Content-Type', /json/)
    .expect(200);

  // process.argv.pop();
});

describe('POST /amm/price', () => {
  it('should return 200 for BUY', async () => {
    await request(gatewayApp)
      .post(`/amm/price`)
      .send({
        chain: 'avalanche',
        network: 'avalanche',
        connector: 'openocean',
        quote: 'sAVAX',
        base: 'USDC',
        amount: '0.01',
        side: 'BUY',
      })
      .set('Accept', 'application/json')
      .expect(200)
      .then((res: any) => {
        expect(res.body.amount).toEqual('0.010000');
        expect(res.body.rawAmount).toEqual('10000');
      });
  });

  it('should return 200 for SELL', async () => {
    await request(gatewayApp)
      .post(`/amm/price`)
      .send({
        chain: 'avalanche',
        network: 'avalanche',
        connector: 'openocean',
        quote: 'USDC',
        base: 'sAVAX',
        amount: '10000',
        side: 'SELL',
      })
      .set('Accept', 'application/json')
      .expect(200)
      .then((res: any) => {
        expect(res.body.amount).toEqual('10000.000000000000000000');
        expect(res.body.rawAmount).toEqual('10000000000000000000000');
      });
  });

  it('should return 500 for unrecognized quote symbol', async () => {
    await request(gatewayApp)
      .post(`/amm/price`)
      .send({
        chain: 'avalanche',
        network: 'avalanche',
        connector: 'openocean',
        quote: 'USDC',
        base: 'bDAI',
        amount: '10000',
        side: 'SELL',
      })
      .set('Accept', 'application/json')
      .expect(500);
  });

  it('should return 500 for unrecognized base symbol', async () => {
    await request(gatewayApp)
      .post(`/amm/price`)
      .send({
        chain: 'avalanche',
        network: 'avalanche',
        connector: 'openocean',
        quote: 'USDC',
        base: 'bDAI',
        amount: '10000',
        side: 'SELL',
      })
      .set('Accept', 'application/json')
      .expect(500);
  });
});

describe('POST /amm/trade', () => {
  it('should return 200 for BUY', async () => {
    await request(gatewayApp)
      .post(`/amm/trade`)
      .send({
        chain: 'avalanche',
        network: 'avalanche',
        connector: 'openocean',
        quote: 'USDC',
        base: 'sAVAX',
        amount: '10000',
        address,
        side: 'BUY',
        nonce: 21,
      })
      .set('Accept', 'application/json')
      .expect(200)
      .then((res: any) => {
        expect(res.body.nonce).toEqual(21);
      });
  });

  it('should return 200 for BUY without nonce parameter', async () => {
    await request(gatewayApp)
      .post(`/amm/trade`)
      .send({
        chain: 'avalanche',
        network: 'avalanche',
        connector: 'openocean',
        quote: 'USDC',
        base: 'sAVAX',
        amount: '10000',
        address,
        side: 'BUY',
      })
      .set('Accept', 'application/json')
      .expect(200);
  });

  it('should return 200 for SELL', async () => {
    await request(gatewayApp)
      .post(`/amm/trade`)
      .send({
        chain: 'avalanche',
        network: 'avalanche',
        connector: 'openocean',
        quote: 'USDC',
        base: 'sAVAX',
        amount: '0.001',
        address,
        side: 'SELL',
        nonce: 21,
      })
      .set('Accept', 'application/json')
      .expect(200)
      .then((res: any) => {
        console.log(res.body);
        expect(res.body.nonce).toEqual(21);
      });
  });
});
