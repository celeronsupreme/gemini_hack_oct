import { writeFileSync } from 'node:fs';
writeFileSync('ts/index.ts', `export * from './contracts';\n`);
console.log('contracts.ts + index.ts written');
