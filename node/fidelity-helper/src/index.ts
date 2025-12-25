/**
 * Retrieve Fidelity transaction data via fetch calls to fidelity.com.
 *
 * @example
 * ```typescript
 * import { Fidelity } from '@righteffort/fidelity-helper';
 *
 * // In this example the callback assumes page.evaluate is provided by your browser
 * // automation framework.
 * const fidelity = new Fidelity(async (fn, ...args) => page.evaluate(fn, ...args));
 *
 * // Get transactions for specific accounts and date range
 * const transactions = await fidelity.getTransactions(
 *     ["123456789", "987654321"],
 *     new Date(2024, 0, 1),
 *     new Date(2024, 0, 31)
 * );
 *
 * for (const t of transactions) {
 *     console.log(`${t.date.toISOString().split('T')[0]}\t$${t.amount}\t${t.description}`);
 * }
 * ```
 * See [fidelity-example.ts](https://github.com/righteffort/finance-helper/tree/main/node/fidelity-example/src/fidelity-example.ts) for a working example.
 *
 * @module
 */

export { Fidelity } from './fidelity.js';
export type { Account, Transaction, EvaluateFunc } from './fidelity.js';
