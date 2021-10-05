/* eslint-disable @typescript-eslint/ban-types */
import { NextFunction, Router, Request, Response } from 'express';
import { Ethereum } from './ethereum';
import { EthereumConfig } from './ethereum.config';
import { ConfigManager } from '../../services/config-manager';
import { verifyEthereumIsAvailable } from './ethereum-middlewares';
import { asyncHandler } from '../../services/error-handler';
import {
  approve,
  allowances,
  balances,
  nonce,
  poll,
} from './ethereum.controllers';
import {
  EthereumNonceRequest,
  EthereumAllowancesRequest,
  EthereumBalanceRequest,
  EthereumApproveRequest,
  EthereumPollRequest,
  EthereumNonceResponse,
  EthereumAllowancesResponse,
  EthereumBalanceResponse,
  EthereumApproveResponse,
  EthereumPollResponse,
} from './ethereum.requests';

export namespace EthereumRoutes {
  export const router = Router();
  export const ethereum = Ethereum.getInstance();
  export const reload = (): void => {
    // ethereum = Ethereum.reload();
  };

  router.use(asyncHandler(verifyEthereumIsAvailable));

  router.get(
    '/',
    asyncHandler(async (_req: Request, res: Response) => {
      let rpcUrl;
      if (ConfigManager.config.ETHEREUM_CHAIN === 'mainnet') {
        rpcUrl = EthereumConfig.config.mainnet.rpcUrl;
      } else {
        rpcUrl = EthereumConfig.config.kovan.rpcUrl;
      }

      res.status(200).json({
        network: ConfigManager.config.ETHEREUM_CHAIN,
        rpcUrl: rpcUrl,
        connection: true,
        timestamp: Date.now(),
      });
    })
  );

  router.post(
    '/nonce',
    asyncHandler(
      async (
        req: Request<{}, {}, EthereumNonceRequest>,
        res: Response<EthereumNonceResponse | string, {}>
      ) => {
        const response = await nonce(req.body);
        res.status(200).json(response);
      }
    )
  );

  router.post(
    '/allowances',
    asyncHandler(
      async (
        req: Request<{}, {}, EthereumAllowancesRequest>,
        res: Response<EthereumAllowancesResponse | string, {}>
      ) => {
        const response = await allowances(req.body);
        res.status(200).json(response);
      }
    )
  );

  router.post(
    '/balances',
    asyncHandler(
      async (
        req: Request<{}, {}, EthereumBalanceRequest>,
        res: Response<EthereumBalanceResponse | string, {}>,
        _next: NextFunction
      ) => {
        res.status(200).json(await balances(req.body));
      }
    )
  );

  router.post(
    '/approve',
    asyncHandler(
      async (
        req: Request<{}, {}, EthereumApproveRequest>,
        res: Response<EthereumApproveResponse | string, {}>
      ) => {
        const result = await approve(req.body);
        return res.status(200).json(result);
      }
    )
  );

  router.post(
    '/poll',
    asyncHandler(
      async (
        req: Request<{}, {}, EthereumPollRequest>,
        res: Response<EthereumPollResponse, {}>
      ) => {
        const result = await poll(req.body);
        res.status(200).json(result);
      }
    )
  );
}
