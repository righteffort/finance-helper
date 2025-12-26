/**
 * Retrieve Fidelity transaction data via fetch calls to fidelity.com.
 */

import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';
import Mustache from 'mustache';
import { Temporal } from '@js-temporal/polyfill';
import type {
  GetTransactionsRespModel,
  GetTransactionsRespHistoryModel,
  GetTransactionsReqModel,
  GetAccountsRespModel,
} from './fidelity-models.js';

/** Fidelity account. */
export interface Account {
  /** Fidelity account number. */
  number: string;
  /** Fidelity account name selected by the account owner. */
  name: string;
}

/** Fidelity transaction. */
export interface Transaction {
  /** Fidelity account number. */
  acct_num: string;
  /** Transaction date. Will always have time 00:00:00, time zone UTC but represent America/New_York. */
  date: Date;
  /** Transaction description. */
  description: string;
  /** Transaction amount in dollars. */
  amount: number;
  /** Transaction identifier. Unique for this account. undefined only if pending. */
  order_number: string | undefined;
  /** True iff transaction is pending. */
  pending: boolean;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type EvaluateFunc = <T>(fn: (...args: any[]) => T, ...args: any[]) => Promise<T>;

/**
 * Raised on any error specific to `Fidelity` class.
 */
export class FidelityError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'FidelityError';
  }
}

/**
 * Retrieve transactions from fidelity.com via browser fetch calls.
 */
export class Fidelity {
  private evaluator: EvaluateFunc;
  private accounts: Map<string, Account> | null = null;
  private static readonly FIDELITY_ZONE = 'America/New_York';

  /**
   * Initialize new instance.
   * @param evaluator - async callback that calls evaluate in context of the browser.
   */
  constructor(evaluator: EvaluateFunc) {
    this.evaluator = evaluator;
  }

  /**
   * Retrieve transactions for the logged in user.
   * @param accounts - list of Fidelity account numbers to retrieve.
   * @param start - start date, inclusive. Date with 00:00:00 and timezone UTC, or YYYY-MM-DD string. Interpreted as midnight America/New_York.
   * @param end - end date, inclusive. See description of start.
   * @returns Transactions for accounts between [start, end].
   * @throws {FidelityError} if there is any error retrieving the transactions.
   */
  async getTransactions(accounts: string[], start: Date | string, end: Date | string): Promise<Transaction[]> {
    const startDate = start instanceof Date ? start : new Date(`${start}T00:00:00Z`);
    const endDate = end instanceof Date ? end : new Date(`${end}T00:00:00Z`);
    Fidelity.checkStartEnd(startDate, endDate);
    const acctDict = new Map<string, Account | null>();
    for (const acct of accounts) {
      acctDict.set(acct, await this.getAccount(acct));
    }

    const missing = Array.from(acctDict.entries())
      .filter(([, account]) => account === null)
      .map(([acctNum]) => acctNum);

    if (missing.length > 0) {
      throw new FidelityError(`Account(s) not found: ${missing.join(', ')}`);
    }

    const accts = Array.from(acctDict.values()).filter((a): a is Account => a !== null);

    const respJson = await this.fetch(
      'https://digital.fidelity.com/ftgw/digital/webactivity/api/graphql?ref_at=activity',
      Fidelity._getTransactionsOptions(accts, startDate, endDate)
    );

    try {
      const resp = respJson as GetTransactionsRespModel;
      const historys = resp.data.getTransactions.historys;
      return historys.map(h => Fidelity.historyEntryToTransaction(h));
    } catch (e) {
      throw new FidelityError(`Failed to parse get_transactions response: ${e instanceof Error ? e.message : String(e)}`);
    }
  }

  /**
   * Return the options argument for calling fetch to get accounts.
   * @returns JSON-compatible object options argument for fetch call.
   */
  static getAccountsOptions(): object {
    return JSON.parse(fs.readFileSync(path.join(packageDir, '../fidelity-templates/getAccountsOptions.json'), 'utf8'));
  }

  /**
   * Return the options argument for calling fetch to get transactions.
   * @param accounts - list of Fidelity accounts to retrieve.
   * @param start - start date, inclusive. Date with 00:00:00 and timezone UTC, or YYYY-MM-DD string. Interpreted as midnight America/New_York.
   * @param end - end date, inclusive. See description of start.
   * @returns JSON-compatible object options argument for fetch call.
   */
  static getTransactionsOptions(accounts: Account[], start: Date | string, end: Date | string): object {
    const startDate = start instanceof Date ? start : new Date(`${start}T00:00:00Z`);
    const endDate = end instanceof Date ? end : new Date(`${end}T00:00:00Z`);
    Fidelity.checkStartEnd(startDate, endDate);
    return Fidelity._getTransactionsOptions(accounts, startDate, endDate);
  }

  /**
   * Convert date to epoch seconds in Fidelity time zone (America/New_York).
   * @param d - date to convert.
   * @returns Epoch seconds for d interpreted as America/New_York at midnight.
   */
  static fidelityEpochSeconds(d: Date): string {
    const fidelityEpochSeconds = Temporal.PlainDate.from({
      year: d.getUTCFullYear(),
      month: d.getUTCMonth() + 1,
      day: d.getUTCDate()
    }).toZonedDateTime(Fidelity.FIDELITY_ZONE)
    return Math.floor(fidelityEpochSeconds.epochMilliseconds / 1000).toString();
  }

  /**
   * Encode name for use in Fidelity get transactions.
   * @param name - the plain-text name.
   * @returns The encoded name.
   */
  static encodeAccountName(name: string): string {
    return Buffer.from(name, 'utf8').toString('base64');
  }

  /**
   * Human-friendly rendering of options used to get transactions.
   * @param options - fetch options arg, e.g. result of {@link getTransactionsOptions}.
   * @returns Printable string with embedded JSON strings parsed into objects.
   */
  static printFetchTransactionsOptions(options: { body: string; [key: string]: unknown }): string {
    const {body, ...optionsMinusBody} = options;
    const bodyObj = JSON.parse(body) as GetTransactionsReqModel;
    const {query, ...bodyMinusQuery} = bodyObj;

    return [
      `options_minus_body=${JSON.stringify(optionsMinusBody, null, 2)}`,
      `body_minus_query=${JSON.stringify(bodyMinusQuery, null, 2)}`,
      `query=${query}`
    ].join('\n');
  }

  private async fetch(url: string, options: object): Promise<object> {
    const resp = await this.evaluator(
      async (url: string, options: object) => {
	const r = await fetch(url, options);
	if (!r.ok) {
          return { status: r.status, text: await r.text() };
	}
	const json = await r.json();
	return { status: r.status, json: json };
      },
      url, options) as FetchResp;
    if (resp.status !== 200) {
      throw new FidelityError(`get_transactions fetch failed, code: ${resp.status}, text: ${resp.text}`);
    }
    return resp.json;
  }

  private static _getTransactionsOptions(accounts: Account[], start: Date, end: Date): object {
    const context = {
      body: JSON.stringify(JSON.stringify(Fidelity.getTransactionsBody(accounts, start, end)))
    };
    return JSON.parse(Mustache.render(Fidelity.getTransactionsOptionsTemplate(), context));
  }

  private static checkStartEnd(start: Date, end: Date) {
    const checkDate = (d: Date) => {
      const dayOffset = d.getUTCHours() + d.getUTCMinutes() / 60 + d.getUTCSeconds() / 3600 + d.getUTCMilliseconds() / 3600000;
      return dayOffset != 0 ? `not exact day: ${dayOffset} hours` : "";
    };
    const outOfOrder = start > end ? "start > end" : "";
    const dateMessage = [checkDate(start), checkDate(end), outOfOrder].filter(m => m.length > 0).join('; ');
    if (dateMessage.length > 0) {
      throw new FidelityError(`Invalid date(s): ${dateMessage}`);
    }
  }

  private async getAccount(account: string): Promise<Account | null> {
    const accounts = await this.getAccounts();
    return accounts.get(account) || null;
  }

  private async getAccounts(): Promise<Map<string, Account>> {
    if (this.accounts !== null) {
      return this.accounts;
    }
    this.accounts = await this.fetchAccounts();
    return this.accounts;
  }

  private async fetchAccounts(): Promise<Map<string, Account>> {
    const respJson = await this.fetch(
      'https://digital.fidelity.com/ftgw/digital/portfolio/api/graphql?ref_at=portsum',
      Fidelity.getAccountsOptions()
    );

    try {
      const resp = respJson as GetAccountsRespModel;
      const context = resp.data.getContext;
      const status = context.sysStatus.backend.account;

      if (status.toLowerCase() !== 'ok') {
        throw new FidelityError(`Fidelity backend not ok ${status}`);
      }

      const accounts = context.person.assets.map(a => ({
        number: a.acctNum,
        name: a.preferenceDetail.name
      }));

      const accountMap = new Map<string, Account>();
      accounts.forEach(a => accountMap.set(a.number, a));
      return accountMap;
    } catch (e) {
      throw new FidelityError(`Failed to parse get_accounts response: ${e instanceof Error ? e.message : String(e)}`);
    }
  }

  private static getTransactionsBody(accounts: Account[], start: Date, end: Date): GetTransactionsReqModel {
    const accountDicts = accounts.map((a, i) => ({
      number: a.number,
      name: Fidelity.encodeAccountName(a.name),
      last: i === accounts.length - 1
    }));

    const context = {
      accounts: accountDicts,
      start: Fidelity.fidelityEpochSeconds(start),
      end: Fidelity.fidelityEpochSeconds(end)
    };

    const body = Mustache.render(Fidelity.getTransactionsBodyTemplate(), context);
    return JSON.parse(body) as GetTransactionsReqModel;  // TODO(aider): this needs to fail at runtime if body does not conform to the model, as happens with pydantic.
  }

  private static getTransactionsBodyTemplate(): string {
    return fs.readFileSync(path.join(packageDir, '../fidelity-templates/getTransactionsBody.json.mustache'), 'utf8');
  }

  private static getTransactionsOptionsTemplate(): string {
    return fs.readFileSync(path.join(packageDir, '../fidelity-templates/getTransactionsOptions.json.mustache'), 'utf8');
  }

  private static historyEntryToTransaction(h: GetTransactionsRespHistoryModel): Transaction {
    // Parse date as UTC with time 00:00:00, representing America/New_York
    const d = new Date(h.date);
    const date = new Date(Date.UTC(d.getFullYear(), d.getMonth(), d.getDate()));

    const amount = parseFloat(h.amount.replace(/[,$]/g, ''));

    return {
      acct_num: h.acctNum,
      date: date,
      description: h.description,
      amount: Math.round(amount * 100) / 100,
      order_number: h.orderNumber || undefined,
      pending: h.intradayInd
    };
  }
}

const packageDir = path.dirname(fileURLToPath(import.meta.url));

interface FetchResp {
  status: number;
  text?: string;
  json: object;
}
