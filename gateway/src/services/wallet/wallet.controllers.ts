import fse from 'fs-extra';
import { Avalanche } from '../../chains/avalanche/avalanche';
import { Ethereum } from '../../chains/ethereum/ethereum';

import {
  AddWalletRequest,
  RemoveWalletRequest,
  GetWalletResponse,
} from './wallet.requests';
import { ConfigManagerCertPassphrase } from '../config-manager-cert-passphrase';

const walletPath = './conf/wallets';

export async function mkdirIfDoesNotExist(path: string): Promise<void> {
  const exists = await fse.pathExists(path);
  if (!exists) {
    await fse.mkdir(path, { recursive: true });
  }
}

export async function addWallet(
  ethereum: Ethereum,
  avalanche: Avalanche,
  req: AddWalletRequest
): Promise<void> {
  const passphrase = ConfigManagerCertPassphrase.readPassphrase();
  if (!passphrase) {
    throw new Error('There is no passphrase');
  }
  let address: string;
  let encryptedPrivateKey: string;
  if (req.chainName === 'ethereum') {
    address = ethereum.getWallet(req.privateKey).address;
    encryptedPrivateKey = await ethereum.encrypt(req.privateKey, passphrase);
  } else if (req.chainName === 'avalanche') {
    address = avalanche.getWallet(req.privateKey).address;
    encryptedPrivateKey = await avalanche.encrypt(req.privateKey, passphrase);
  } else {
    throw new Error('unrecognized chain name');
  }

  const path = `${walletPath}/${req.chainName}`;
  await mkdirIfDoesNotExist(path);
  await fse.writeFile(`${path}/${address}.json`, encryptedPrivateKey);
}

// if the file does not exist, this should not fail
export async function removeWallet(req: RemoveWalletRequest): Promise<void> {
  await fse.rm(`./conf/wallets/${req.chainName}/${req.address}.json`, {
    force: true,
  });
}

export async function getDirectories(source: string): Promise<string[]> {
  const files = await fse.readdir(source, { withFileTypes: true });
  return files
    .filter((dirent) => dirent.isDirectory())
    .map((dirent) => dirent.name);
}

export function getLastPath(path: string): string {
  return path.split('/').slice(-1)[0];
}

export function dropExtension(path: string): string {
  return path.substr(0, path.lastIndexOf('.')) || path;
}

export async function getJsonFiles(source: string): Promise<string[]> {
  const files = await fse.readdir(source, { withFileTypes: true });
  return files
    .filter((f) => f.isFile() && f.name.endsWith('.json'))
    .map((f) => f.name);
}

export async function getWallets(): Promise<GetWalletResponse[]> {
  const chains = await getDirectories(walletPath);

  const responses: GetWalletResponse[] = [];

  for (const chain of chains) {
    const walletFiles = await getJsonFiles(`${walletPath}/${chain}`);

    const response: GetWalletResponse = { chain, walletAddresses: [] };

    for (const walletFile of walletFiles) {
      const address = dropExtension(getLastPath(walletFile));
      response.walletAddresses.push(address);
    }

    responses.push(response);
  }

  return responses;
}
