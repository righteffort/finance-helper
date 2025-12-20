import puppeteer from 'puppeteer';
import * as readline from 'readline';
import { Fidelity } from 'fidelity-helper';
import { Command } from 'commander';
import { z } from 'zod';

const program = new Command();

const optionsSchema = z.object({
  accounts: z.array(z.string()),
  start: z.iso.date('Must be valid ISO YYYY-MM-DD date'),
  end: z.iso.date('Must be valid ISO YYYY-MM-DD date'),
}).refine((options) => options.start <= options.end,
  {message: 'start must be less than or equal to end', path: ['start,end']});

program
  .requiredOption('-a, --accounts <str...>', 'Account name(s)')
  .requiredOption('-s, --start <date>', 'Start date in YYYY-MM-DD, interpreted in America/New_York')
  .requiredOption('-e, --end <date>', 'End date in YYYY-MM-DD, interpreted in America/New_York')
  .action(async options => {
    const result = optionsSchema.safeParse(options);
    if (!result.success) {
      result.error.issues.forEach(err => {
        console.error(`${err.path.join('.')}: ${err.message}`);
      });
      process.exit(1);
    }
    const start = new Date(result.data.start + "T00:00:00Z");
    const end = new Date(result.data.end + "T00:00:00Z");
    await getTransactions(result.data.accounts, start, end);
  });

program.parse(process.argv);

async function getTransactions(accounts: string[], start: Date, end: Date) {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout
  });

  const browser = await puppeteer.launch({ headless: false });
  const page = await browser.newPage();
  await page.goto('https://www.fidelity.com')
  const fidelity = new Fidelity(async (fn, ...args) => {
    return page.evaluate(fn, ...args);
  });
  // can also simply pass `page.evaluate.bind(page)` instead of wrapping

  await new Promise<void>((resolve) => {
    rl.question('Login to Fidelity, then press Enter: ', () => {
      resolve();
    });
  });

  const transactions = await fidelity.getTransactions(accounts, start, end);
  console.log(`transactions=${JSON.stringify(transactions, null, 2)}`);

  await new Promise<void>((resolve) => {
    rl.question('Press Enter to exit: ', () => {
      rl.close();
      resolve();
    });
  });

  await browser.close();
}
