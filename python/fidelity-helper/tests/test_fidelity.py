import json
from datetime import date
from typing import cast
from unittest.mock import patch

import aiofiles
import pytest

from fidelity_helper.fidelity import Account, Fidelity
from fidelity_helper.fidelity_models import GetTransactionsReqModel


class MockEvaluator:
    async def __call__(self, code: str) -> object:
        """Helper function to mock fetch responses based on URL in the code."""
        if "ftgw/digital/portfolio/api/graphql?ref_at=portsum" in code:
            async with aiofiles.open("testdata/mock_get_accounts_response.json") as f:
                content = await f.read()
                return cast(object, json.loads(content))
        elif "ftgw/digital/webactivity/api/graphql?ref_at=activity" in code:
            async with aiofiles.open(
                "testdata/mock_get_transactions_response.json"
            ) as f:
                content = await f.read()
                return cast(object, json.loads(content))
        pytest.fail(f"Unexpected code in mock_evaluator: {code}")


def test_get_transactions_options() -> None:
    accts = [Account(number="1234", name="name1"), Account(number="6789", name="name2")]
    start = date(2025, 9, 30)
    end = date(2025, 10, 1)
    options = Fidelity.get_transactions_options(accts, start, end)
    body = GetTransactionsReqModel.model_validate_json(cast(str, options["body"]))
    assert body.variables.acctIdList == "1234,6789"
    assert [a.acctNum for a in body.variables.acctDetailList] == ["1234", "6789"]
    assert [a.name for a in body.variables.acctDetailList] == ["bmFtZTE=", "bmFtZTI="]
    search_criteria = body.variables.searchCriteriaDetail
    assert search_criteria.txnFromDate == "1759204800"
    assert search_criteria.txnToDate == "1759291200"


@pytest.mark.asyncio
async def test_get_transactions() -> None:
    mock_evaluator = MockEvaluator()
    fidelity = Fidelity(mock_evaluator)
    accounts = ["1234", "5678"]
    start = date(2025, 11, 28)
    end = date(2025, 12, 2)

    with patch.object(fidelity, "_fetch", wraps=fidelity._fetch) as fetch_spy:  # pyright: ignore[reportPrivateUsage]
        transactions = await fidelity.get_transactions(accounts, start, end)
    assert fetch_spy.call_count == 2
    options = cast(
        dict[str, object], json.loads(cast(str, fetch_spy.call_args_list[1].args[1]))
    )
    body = GetTransactionsReqModel.model_validate_json(cast(str, options["body"]))
    search_criteria_detail = body.variables.searchCriteriaDetail
    assert search_criteria_detail.txnFromDate == "1764306000"
    assert search_criteria_detail.txnToDate == "1764651600"

    # Load expected results
    async with aiofiles.open("testdata/get_transactions_expected.json") as f:
        content = await f.read()
        expected = cast(object, json.loads(content))

    # Convert transactions to dict format for comparison
    actual: list[dict[str, str | float | bool]] = []
    for t in transactions:
        d: dict[str, str | float | bool] = {
            "acct_num": t.acct_num,
            "date": f"{t.date.isoformat()}T00:00:00.000Z",
            "description": t.description,
            "pending": t.pending,
        }
        if t.order_number is not None:
            d["order_number"] = t.order_number
        if t.amount is not None:
            d["amount"] = t.amount
        actual.append(d)

    assert actual == expected
