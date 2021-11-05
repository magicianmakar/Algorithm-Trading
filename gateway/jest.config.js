module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  forceExit: true,
  coveragePathIgnorePatterns: [
    'src/app.ts',
    'src/https.ts',
    'src/services/ethereum-base.ts',
    'src/chains/ethereum/ethereum.ts',
    'src/chains/ethereum/uniswap/uniswap.ts',
    'src/chains/ethereum/avalanche.ts',
    'src/chains/ethereum/pangolin/pangolin.ts',
  ],
  modulePathIgnorePatterns: ['<rootDir>/dist/'],
};
