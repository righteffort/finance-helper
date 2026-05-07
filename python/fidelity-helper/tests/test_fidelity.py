import json
from dataclasses import asdict
from datetime import date
from pathlib import Path
from typing import cast
from unittest.mock import patch

import aiofiles
import pytest

from fidelity_helper.fidelity import Account, Fidelity
from fidelity_helper.fidelity_models import GetTransactionsReqModel


def get_suffixes() -> list[str]:
    """Discover available test suffixes from testdata directory."""
    return sorted(
        p.stem.removeprefix("mock_get_accounts_response_")
        for p in Path("testdata").glob("mock_get_accounts_response_*.json")
    )


class MockEvaluator:
    def __init__(self, suffix: str) -> None:
        self.suffix = suffix

    async def __call__(self, code: str) -> object:
        """Helper function to mock fetch responses based on URL in the code."""
        if "ftgw/digital/portfolio/api/graphql?ref_at=portsum" in code:
            async with aiofiles.open(
                f"testdata/mock_get_accounts_response_{self.suffix}.json"
            ) as f:
                content = await f.read()
                return cast(object, json.loads(content))
        elif "ftgw/digital/webactivity/api/graphql?ref_at=activity" in code:
            async with aiofiles.open(
                f"testdata/mock_get_transactions_response_{self.suffix}.json"
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
@pytest.mark.parametrize("suffix", get_suffixes())
async def test_get_transactions(suffix: str) -> None:
    config = cast(
        dict[str, list[str]],
        json.loads(Path(f"testdata/config_{suffix}.json").read_text()),
    )

    mock_evaluator = MockEvaluator(suffix)
    fidelity = Fidelity(mock_evaluator)
    accounts: list[str] = config["accounts"]
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

    async with aiofiles.open(f"testdata/get_transactions_expected_{suffix}.json") as f:
        content = await f.read()
        expected = cast(object, json.loads(content))

    actual: list[dict[str, str | float | bool]] = []
    for t in transactions:
        d = {
            k: v
            for k, v in cast(dict[str, str | float | bool | None], asdict(t)).items()
            if v is not None
        }
        d["date"] = f"{t.date.isoformat()}T00:00:00.000Z"
        actual.append(d)

    assert actual == expected
