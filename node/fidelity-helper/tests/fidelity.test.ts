import { readFileSync, readdirSync } from 'fs';
import { join } from 'path';
import { Fidelity } from '../src/fidelity.js';
import type { GetTransactionsFetchInitPartial, GetTransactionsReqModel } from '../src/fidelity-models.js';
import { describe, it, expect } from 'vitest';

const TESTDATA = join(__dirname, 'testdata');

function getSuffixes(): string[] {
  return readdirSync(TESTDATA)
    .map(name => name.match(/^mock_get_accounts_response_(.+)\.json$/)?.[1])
    .filter((s): s is string => s !== undefined)
    .sort();
}

class MockEvaluator {
  constructor(
    private readonly suffix: string,
    private readonly expectedStart: string,
    private readonly expectedEnd: string,
  ) {}

  async evaluate(_fn: Function, ...args: any[]): Promise<any> {
    const url = args[0];
    if (typeof url === 'string') {
      if (url.endsWith('ftgw/digital/portfolio/api/graphql?ref_at=portsum')) {
        return JSON.parse(readFileSync(join(TESTDATA, `mock_get_accounts_response_${this.suffix}.json`), 'utf8'));
      } else if (url.endsWith('ftgw/digital/webactivity/api/graphql?ref_at=activity')) {
        const { body } = args[1] as GetTransactionsFetchInitPartial;
        const bodyObj = JSON.parse(body) as GetTransactionsReqModel;
        expect(bodyObj.variables.searchCriteriaDetail.txnFromDate).toBe(this.expectedStart);
        expect(bodyObj.variables.searchCriteriaDetail.txnToDate).toBe(this.expectedEnd);
        return JSON.parse(readFileSync(join(TESTDATA, `mock_get_transactions_response_${this.suffix}.json`), 'utf8'));
      }
    }
    expect.fail(`Unexpected args[0] in test: ${url}`);
  }
}

describe('Fidelity', () => {
  for (const suffix of getSuffixes()) {
    it(`should get transactions [${suffix}]`, async () => {
      const config = JSON.parse(readFileSync(join(TESTDATA, `config_${suffix}.json`), 'utf8'));

      const mockEvaluator = new MockEvaluator(suffix, "1764306000", "1764651600");
      const fidelity = new Fidelity(mockEvaluator.evaluate.bind(mockEvaluator));
      const accounts: string[] = config.accounts;
      const start = new Date('2025-11-28T00:00:00.000Z');
      const end = new Date('2025-12-02T00:00:00.000Z');

      // Load expected results
      const expected = JSON.parse(readFileSync(join(TESTDATA, `get_transactions_expected_${suffix}.json`), 'utf8'));

      const transactions = await fidelity.getTransactions(accounts, start, end);
      // Convert transactions to plain objects for comparison, converting to python style field names
      const actual = transactions.map(t => ({
        acct_num: t.acctNum,
        ...(t.amount !== undefined && {amount: t.amount}),
        ...(t.cashBalance !== undefined && {cash_balance: t.cashBalance}),
        date: t.date.toISOString(),
        description: t.description,
        ...(t.orderNumber !== undefined && {order_number: t.orderNumber}),
        pending: t.pending,
      }));

      expect(actual).toEqual(expected);
    });
  }
});
