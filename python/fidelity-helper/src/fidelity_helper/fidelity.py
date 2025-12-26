"""Retrieve transactions from fidelity.com via browswer fetch calls."""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from http import HTTPStatus
from importlib.resources import files
from typing import TYPE_CHECKING, Any, TypedDict, cast
from zoneinfo import ZoneInfo

from .fidelity_models import (
    GetAccountsRespModel,
    GetTransactionsReqModel,
    GetTransactionsRespHistoryModel,
    GetTransactionsRespModel,
)


if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

import pystache  # pyright: ignore[reportMissingTypeStubs]
from pydantic import ValidationError


class FidelityError(Exception):
    """Raised on any error specific to `Fidelity` class."""


@dataclass
class Account:
    """Fidelity account."""

    number: str
    """Fidelity account number."""
    name: str
    """Fidelity account name selected by the account owner."""


@dataclass
class Transaction:
    """Fidelity transaction."""

    acct_num: str
    """Fidelity account number."""
    date: date
    """Transaction date. Should be interpreted as midnight America/New_York."""
    description: str
    """Transaction description."""
    amount: float | None
    """Transaction amount in dollars. May be `None` if pending."""
    order_number: str | None
    """Transaction identifier. Unique for this account. `None` only if pending."""
    pending: bool
    """True iff transaction is pending."""


class Fidelity:
    """Retrieve transactions from fidelity.com via browser fetch calls."""

    def __init__(
        self,
        evaluator: Callable[[str], Awaitable[Any]],  # pyright: ignore[reportExplicitAny]
    ) -> None:
        """Initialize new instance.

        Args:
            evaluator: async callback that calls evaluate in context of the browser.

        """
        self._accounts: dict[str, Account] | None = None
        self._evaluator = evaluator

    async def get_transactions(
        self, accounts: list[str], start: date, end: date
    ) -> list[Transaction]:
        """Retrieve transactions for the logged in user.

        Args:
            accounts: list of Fidelity account numbers to retrieve.
            start: start date, inclusive. Treated as midnight America/New_York.
            end: end date, inclusive. Treated as midnight America/New_York.

        Returns:
            Transactions for accounts between [start, end].

        Raises:
            FidelityError: if there is any error retrieving the transactions.

        """
        acct_dict = {a: await self._get_account(a) for a in accounts}
        missing = [a for a, acct in acct_dict.items() if acct is None]
        if missing:
            msg = f"Account(s) not found: {', '.join(missing)}"
            raise FidelityError(msg)
        accts = [a for a in acct_dict.values() if a is not None]

        resp_json = await self._fetch(
            "https://digital.fidelity.com/ftgw/digital/webactivity/api/graphql?ref_at=activity",
            json.dumps(Fidelity.get_transactions_options(accts, start, end)),
        )
        try:
            historys = GetTransactionsRespModel.model_validate(
                resp_json
            ).data.getTransactions.historys
        except ValidationError as e:
            msg = "Failed to parse get_transactions response"
            raise FidelityError(msg) from e
        return [Fidelity._history_entry_to_transaction(h) for h in historys]

    async def get_accounts(self) -> list[Account]:
        """Retrieve accounts for the logged in user.

        Returns:
            User's accounts.

        Raises:
            FidelityError: if there is any error retrieving the transactions.

        """
        return list((await self._get_accounts()).values())

    @staticmethod
    def get_transactions_options(
        accounts: list[Account], start: date, end: date
    ) -> dict[str, object]:
        """Return the [options](https://developer.mozilla.org/en-US/docs/Web/API/Window/fetch#options) argument for calling fetch to get transactions.

        Args:
            accounts: list of Fidelity accounts to retrieve.
            start: start date, inclusive. Treated as midnight America/New_York.
            end: end date, inclusive. Treated as midnight America/New_York.

        Returns:
           JSON-compatible object options argument for fetch call.

        """  # noqa: E501
        context = {
            "body": json.dumps(
                Fidelity._get_transactions_body(accounts, start, end).model_dump_json()
            )
        }
        return cast(
            dict[str, object],
            json.loads(
                cast(
                    str,
                    pystache.render(  # pyright: ignore[reportUnknownMemberType]
                        Fidelity._get_transactions_options_template(), context
                    ),
                )
            ),
        )

    @staticmethod
    def get_accounts_options() -> dict[str, object]:
        """Return the <a href="https://developer.mozilla.org/en-US/docs/Web/API/Window/fetch#options" target="_blank">options</a> argument for calling fetch to get accounts.

        Returns:
           JSON-compatible object options argument for fetch call.

        """  # noqa: E501
        return cast(
            dict[str, object],
            json.loads(
                files("fidelity_helper")
                .joinpath("fidelity-templates/getAccountsOptions.json")
                .read_text()
            ),
        )

    _FIDELITY_ZONE = ZoneInfo("America/New_York")

    @staticmethod
    def fidelity_date(d: date) -> int:
        """Convert date to epoch seconds in Fidelity time zone (America/New_York).

        Arguments:
            d(date): date to convert.

        Returns:
            Epoch seconds for d interpreted as America/New_York at midnight.

        """
        return int(
            datetime.combine(
                d, datetime.min.time(), Fidelity._FIDELITY_ZONE
            ).timestamp()
        )

    @staticmethod
    def encode_account_name(name: str) -> str:
        """Encode name for use in Fidelity get transactions.

        Args:
            name: the plain-text name.

        Returns:
            The encoded name.

        """
        return base64.b64encode(name.encode("utf-8")).decode("ascii")

    @staticmethod
    def print_get_transactions_options(options: dict[str, object]) -> str:
        """Human-friendly rendering of options used to get transactions.

        Args:
            options: JSON-compatible object for fetch options arg.

        Returns:
            Printable string with embedded JSON strings parsed into objects.

        """
        options_minus_body = cast(dict[str, object], json.loads(json.dumps(options)))
        del options_minus_body["body"]
        body = cast(dict[str, object], json.loads(cast(str, options["body"])))
        body_minus_query = cast(dict[str, object], json.loads(json.dumps(body)))
        del body_minus_query["query"]
        query = cast(str, body["query"])
        return "\n".join(
            [
                f"options_minus_body={json.dumps(options_minus_body, indent=2)}",
                f"body_minus_query={json.dumps(body_minus_query, indent=2)}",
                "query=" + query,
            ]
        )

    async def _fetch(self, url: str, options_str: str) -> dict[str, object]:
        fetch = f'fetch("{url}", {options_str})'
        script = f"""
        (async () => {{
             const r = await {fetch};
             if (!r.ok) {{
                 return {{ status: r.status, text: await r.text() }}
             }}
             const json = await r.json()
             return {{ status: r.status, json: json }};
        }})()
        """
        resp = cast(_FetchResp, await self._evaluator(script))
        if resp["status"] != HTTPStatus.OK:
            msg = (
                "get_transactions fetch failed, code: ",
                f"{resp['status']}, text: {resp.get('text')}",
            )
            raise FidelityError(msg)
        return resp["json"]

    async def _get_account(self, account: str) -> Account | None:
        return (await self._get_accounts()).get(account, None)

    async def _get_accounts(self) -> dict[str, Account]:
        if self._accounts is not None:
            return self._accounts
        self._accounts = await self._fetch_accounts()
        return self._accounts

    async def _fetch_accounts(self) -> dict[str, Account]:
        resp_json = await self._fetch(
            "https://digital.fidelity.com/ftgw/digital/portfolio/api/graphql?ref_at=portsum",
            json.dumps(Fidelity.get_accounts_options()),
        )
        try:
            resp = GetAccountsRespModel.model_validate(resp_json).data.getContext
        except ValidationError as e:
            msg = "Failed to parse get_accounts response"
            raise FidelityError(msg) from e
        status = resp.sysStatus.backend.account
        if status.lower() != "ok":
            msg = f"Fidelity backend not ok {status}"
            raise FidelityError(msg)
        accounts = [
            Account(number=a.acctNum, name=a.preferenceDetail.name)
            for a in resp.person.assets
        ]
        return {a.number: a for a in accounts}

    @staticmethod
    def _get_transactions_body(
        accounts: list[Account], start: date, end: date
    ) -> GetTransactionsReqModel:
        account_dicts: list[dict[str, str | bool]] = [
            {
                "number": a.number,
                "name": Fidelity.encode_account_name(a.name),
                "last": i == len(accounts) - 1,
            }
            for i, a in enumerate(accounts)
        ]
        context = {
            "accounts": account_dicts,
            "start": str(Fidelity.fidelity_date(start)),
            "end": str(Fidelity.fidelity_date(end)),
        }
        body = cast(
            str,
            pystache.render(Fidelity._get_transactions_body_template(), context),  # pyright: ignore[reportUnknownMemberType]
        )
        return GetTransactionsReqModel.model_validate_json(body)

    @staticmethod
    def _get_transactions_body_template() -> str:
        return (
            files("fidelity_helper")
            .joinpath("fidelity-templates/getTransactionsBody.json.mustache")
            .read_text()
        )

    @staticmethod
    def _get_transactions_options_template() -> str:
        return (
            files("fidelity_helper")
            .joinpath("fidelity-templates/getTransactionsOptions.json.mustache")
            .read_text()
        )

    @staticmethod
    def _history_entry_to_transaction(
        h: GetTransactionsRespHistoryModel,
    ) -> Transaction:
        pending = bool(h.intradayInd)
        try:
            amount = round(float(re.sub(r"[,$]", r"", h.amount)), 2)
        except ValueError as e:
            if not pending:
                msg = f"Unexpected amount string ${h.amount} in history entry ${h}"
                raise FidelityError(msg) from e
            amount = None
        return Transaction(
            acct_num=h.acctNum,
            date=datetime.strptime(h.date, "%b-%d-%Y").date(),
            description=h.description,
            amount=amount,
            order_number=h.orderNumber,
            pending=pending,
        )


class _FetchResp(TypedDict):
    status: int
    text: str
    json: dict[str, Any]  # pyright: ignore[reportExplicitAny]
