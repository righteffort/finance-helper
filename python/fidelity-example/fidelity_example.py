import argparse
import asyncio
import sys
from datetime import date
from typing import cast

import zendriver as zd
from fidelity_helper import Fidelity


async def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser()
    parser.register("type", "date", lambda s: date.fromisoformat(s))  # pyright: ignore[reportUnknownLambdaType, reportUnknownArgumentType]
    _ = parser.add_argument(
        "-a", "--accounts", nargs="+", required=True, help="Account names(s)"
    )
    _ = parser.add_argument(
        "-s",
        "--start",
        type="date",
        required=True,
        help="Start date in YYYY-MM-DD, interpreted in America/New_York",
    )
    _ = parser.add_argument(
        "-e",
        "--end",
        type="date",
        required=True,
        help="End date in YYYY-MM-DD, interpreted in America/New_York",
    )
    args = parser.parse_args(argv)
    driver = await zd.start()
    page = await driver.get("https://www.fidelity.com/")
    fidelity = Fidelity(lambda expr: page.evaluate(expr, await_promise=True))
    _ = input("Login to Fidelity, then press Enter: ")
    ts = await fidelity.get_transactions(
        cast(list[str], args.accounts), cast(date, args.start), cast(date, args.end)
    )
    print(ts)
    await driver.stop()


if __name__ == "__main__":
    x = main
    asyncio.run(main(sys.argv[1:]))
