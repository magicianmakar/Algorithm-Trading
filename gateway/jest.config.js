module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  forceExit: true,
  coveragePathIgnorePatterns: [
    'src/app.ts',
    'src/https.ts',
    'src/paths.ts',
    'src/services/ethereum-base.ts',
    'src/services/telemetry-transport.ts',
    'src/chains/ethereum/ethereum.ts',
    'src/chains/ethereum/uniswap/uniswap.ts',
    'src/chains/avalanche/avalanche.ts',
    'src/chains/avalanche/pangolin/pangolin.ts',
    'conf/migration/migrations.js',
    'src/chains/solana/solana.ts',
    'src/connectors/uniswap/uniswap.config.ts',
  ],
  modulePathIgnorePatterns: ['<rootDir>/dist/'],
  testPathIgnorePatterns: [
    'test/services/evm.nonce.test.ts',
    'test/chains/harmony/harmony.routes.test.ts',
    'test/chains/avalanche/avalanche.routes.test.ts',
    'test/chains/solana/solana.routes.test.ts',
    'test/services/wallet/wallet.routes.test.ts',
    'test/chains/harmony/harmony.routes.test.ts',
    'test/chains/ethereum/sushiswap/sushiswap.routes.test.ts',
    'test/chains/ethereum/uniswap/uniswap.routes.test.ts',
    'test/chains/ethereum/uniswap/uniswap.lp.routes.test.ts',
    'test/network/network.routes.test.ts',
    'test/chains/ethereum/ethereum.routes.test.ts',
    'test/chains/avalanche/pangolin/pangolin.routes.test.ts',
  ],
  setupFilesAfterEnv: ['<rootDir>/test/setupTests.js'],
  globalSetup: '<rootDir>/test/setup.ts',
  globalTeardown: '<rootDir>/test/teardown.ts',
};
