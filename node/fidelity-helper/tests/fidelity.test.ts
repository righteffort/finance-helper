import { readFileSync } from 'fs';
import { join } from 'path';
import { Fidelity } from '../src/fidelity.js';
import type { GetTransactionsFetchInitPartial, GetTransactionsReqModel } from '../src/fidelity-models.js';
import { describe, it, expect } from 'vitest';

class MockEvaluator {
  expected_start: string;
  expected_end: string;
  constructor(expected_start: string, expected_end: string) {
    this.expected_start = expected_start;
    this.expected_end = expected_end;
  }
  async evaluate(_fn: Function, ...args: any[]): Promise<any> {
    const url = args[0];
  
    if (typeof url === 'string') {
      if (url.endsWith('ftgw/digital/portfolio/api/graphql?ref_at=portsum')) {
	const mockData = JSON.parse(readFileSync(join(__dirname, 'testdata/mock_get_accounts_response.json'), 'utf8'));
	return mockData;
      } else if (url.endsWith('ftgw/digital/webactivity/api/graphql?ref_at=activity')) {
	const init = args[1] as GetTransactionsFetchInitPartial;
	const {body} = init;
	const bodyObj = JSON.parse(body) as GetTransactionsReqModel;
	expect(bodyObj.variables.searchCriteriaDetail.txnFromDate).toBe(this.expected_start);
	expect(bodyObj.variables.searchCriteriaDetail.txnToDate).toBe(this.expected_end);
	const mockData = JSON.parse(readFileSync(join(__dirname, 'testdata/mock_get_transactions_response.json'), 'utf8'));
	return mockData;
      }
    }
    expect.fail(`Unexpected args[0] in test: ${url}`);
  }
}

describe('Fidelity', () => {
  it('should get transactions', async () => {
    const mockEvaluator = new MockEvaluator("1764306000", "1764651600");
    const fidelity = new Fidelity(mockEvaluator.evaluate.bind(mockEvaluator));
    const accounts = ['1234', '5678'];
    const start = new Date('2025-11-28T00:00:00.000Z');
    const end = new Date('2025-12-02T00:00:00.000Z');

    const transactions = await fidelity.getTransactions(accounts, start, end);

    // Load expected results
    const expected = JSON.parse(readFileSync(join(__dirname, 'testdata/get_transactions_expected.json'), 'utf8'));
    
    // Convert transactions to plain objects for comparison
    const actual = transactions.map(t => ({
      acct_num: t.acct_num,
      date: t.date.toISOString(),
      description: t.description,
      amount: t.amount,
      order_number: t.order_number,
      pending: t.pending,
    }));

    expect(actual).toEqual(expected);
  });
});
