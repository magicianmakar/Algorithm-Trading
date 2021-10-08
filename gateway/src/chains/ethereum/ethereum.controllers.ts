import { Ethereum } from './ethereum';
import ethers, { constants, Wallet, utils, BigNumber } from 'ethers';
import { ConfigManager } from '../../services/config-manager';
import { latency, bigNumberWithDecimalToStr } from '../../services/base';
import { GatewayError, HttpException } from '../../services/error-handler';
import { UniswapConfig } from './uniswap/uniswap.config';
import { tokenValueToString } from '../../services/base';
import { Token } from '../../services/ethereum-base';

import {
  EthereumAllowancesRequest,
  EthereumAllowancesResponse,
  EthereumApproveRequest,
  EthereumApproveResponse,
  EthereumBalanceResponse,
  EthereumBalanceRequest,
  EthereumCancelRequest,
  EthereumCancelResponse,
  EthereumNonceRequest,
  EthereumNonceResponse,
  EthereumPollRequest,
  EthereumPollResponse,
  EthereumTransactionReceipt,
} from './ethereum.requests';
import {
  validateEthereumAllowancesRequest,
  validateEthereumApproveRequest,
  validateEthereumBalanceRequest,
  validateEthereumNonceRequest,
  validateEthereumPollRequest,
  validateEthereumCancelRequest,
} from './ethereum.validators';

export const ethereum = Ethereum.getInstance();

export async function nonce(
  req: EthereumNonceRequest
): Promise<EthereumNonceResponse> {
  validateEthereumNonceRequest(req);

  // get the address via the private key since we generally use the private
  // key to interact with gateway and the address is not part of the user config
  const wallet = ethereum.getWallet(req.privateKey);
  const nonce = await ethereum.nonceManager.getNonce(wallet.address);
  return { nonce };
}

const getSpender = (reqSpender: string): string => {
  let spender: string;
  if (reqSpender === 'uniswap') {
    if (ConfigManager.config.ETHEREUM_CHAIN === 'mainnet') {
      spender = UniswapConfig.config.mainnet.uniswapV2RouterAddress;
    } else {
      spender = UniswapConfig.config.kovan.uniswapV2RouterAddress;
    }
  } else {
    spender = reqSpender;
  }

  return spender;
};

const getTokenSymbolsToTokens = (
  tokenSymbols: Array<string>
): Record<string, Token> => {
  const tokens: Record<string, Token> = {};

  for (let i = 0; i < tokenSymbols.length; i++) {
    const symbol = tokenSymbols[i];
    const token = ethereum.getTokenBySymbol(symbol);
    if (!token) {
      continue;
    }

    tokens[symbol] = token;
  }

  return tokens;
};

export async function allowances(
  req: EthereumAllowancesRequest
): Promise<EthereumAllowancesResponse | string> {
  validateEthereumAllowancesRequest(req);

  const initTime = Date.now();
  const wallet = ethereum.getWallet(req.privateKey);

  const tokens = getTokenSymbolsToTokens(req.tokenSymbols);

  const spender = getSpender(req.spender);

  const approvals: Record<string, string> = {};
  await Promise.all(
    Object.keys(tokens).map(async (symbol) => {
      approvals[symbol] = tokenValueToString(
        await ethereum.getERC20Allowance(
          wallet,
          spender,
          tokens[symbol].address,
          tokens[symbol].decimals
        )
      );
    })
  );

  return {
    network: ConfigManager.config.ETHEREUM_CHAIN,
    timestamp: initTime,
    latency: latency(initTime, Date.now()),
    spender: spender,
    approvals: approvals,
  };
}

export async function balances(
  req: EthereumBalanceRequest
): Promise<EthereumBalanceResponse | string> {
  validateEthereumBalanceRequest(req);

  const initTime = Date.now();

  let wallet: Wallet;
  try {
    wallet = ethereum.getWallet(req.privateKey);
  } catch (err) {
    throw new HttpException(500, 'Error getting wallet ' + err);
  }

  const tokens = getTokenSymbolsToTokens(req.tokenSymbols);

  const balances: Record<string, string> = {};
  balances.ETH = tokenValueToString(await ethereum.getEthBalance(wallet));
  await Promise.all(
    Object.keys(tokens).map(async (symbol) => {
      if (tokens[symbol] !== undefined) {
        const address = tokens[symbol].address;
        const decimals = tokens[symbol].decimals;
        const balance = await ethereum.getERC20Balance(
          wallet,
          address,
          decimals
        );
        balances[symbol] = tokenValueToString(balance);
      }
    })
  );

  return {
    network: ConfigManager.config.ETHEREUM_CHAIN,
    timestamp: initTime,
    latency: latency(initTime, Date.now()),
    balances: balances,
  };
}

export async function approve(
  req: EthereumApproveRequest
): Promise<EthereumApproveResponse> {
  validateEthereumApproveRequest(req);
  const { amount, nonce, privateKey, token } = req;
  const spender = getSpender(req.spender);

  if (!ethereum.ready()) await ethereum.init();
  const initTime = Date.now();
  let wallet: Wallet;
  try {
    wallet = ethereum.getWallet(privateKey);
  } catch (err) {
    throw new Error(`Error getting wallet ${err}`);
  }
  const fullToken = ethereum.getTokenBySymbol(token);
  if (!fullToken) {
    throw new Error(`Token "${token}" is not supported`);
  }
  const amountBigNumber = amount
    ? utils.parseUnits(amount, fullToken.decimals)
    : constants.MaxUint256;

  // call approve function
  const approval = await ethereum.approveERC20(
    wallet,
    spender,
    fullToken.address,
    amountBigNumber,
    nonce
  );

  return {
    network: ConfigManager.config.ETHEREUM_CHAIN,
    timestamp: initTime,
    latency: latency(initTime, Date.now()),
    tokenAddress: fullToken.address,
    spender: spender,
    amount: bigNumberWithDecimalToStr(amountBigNumber, fullToken.decimals),
    nonce: approval.nonce,
    approval: approval,
  };
}

// TransactionReceipt from ethers uses BigNumber which is not easy to interpret directly from JSON.
// Transform those BigNumbers to string and pass the rest of the data without changes.

const toEthereumTransactionReceipt = (
  receipt: ethers.providers.TransactionReceipt | null
): EthereumTransactionReceipt | null => {
  if (receipt) {
    return {
      ...receipt,
      gasUsed: receipt.gasUsed.toString(),
      cumulativeGasUsed: receipt.cumulativeGasUsed.toString(),
    };
  }

  return null;
};

export async function poll(
  req: EthereumPollRequest
): Promise<EthereumPollResponse> {
  validateEthereumPollRequest(req);

  const initTime = Date.now();
  const receipt = await ethereum.getTransactionReceipt(req.txHash);
  const confirmed = !!receipt && !!receipt.blockNumber;

  if (receipt && receipt.status === 0) {
    const transaction = await ethereum.getTransaction(req.txHash);
    const gasUsed = BigNumber.from(receipt.gasUsed).toNumber();
    const gasLimit = BigNumber.from(transaction.gasLimit).toNumber();
    if (gasUsed / gasLimit > 0.9)
      throw new GatewayError(503, 1003, 'Transaction out of gas.');
  }

  return {
    network: ConfigManager.config.ETHEREUM_CHAIN,
    timestamp: initTime,
    latency: latency(initTime, Date.now()),
    txHash: req.txHash,
    confirmed,
    receipt: toEthereumTransactionReceipt(receipt),
  };
}

export async function cancel(
  req: EthereumCancelRequest
): Promise<EthereumCancelResponse> {
  validateEthereumCancelRequest(req);

  if (!ethereum.ready()) await ethereum.init();
  const initTime = Date.now();
  let wallet: Wallet;
  try {
    wallet = ethereum.getWallet(req.privateKey);
  } catch (err) {
    throw new Error(`Error getting wallet ${err}`);
  }

  // call cancelTx function
  const cancelTx = await ethereum.cancelTx(wallet, req.nonce);

  return {
    network: ConfigManager.config.ETHEREUM_CHAIN,
    timestamp: initTime,
    latency: latency(initTime, Date.now()),
    txHash: cancelTx.hash,
  };
}
