r"""Retrieve Fidelity transaction data via fetch calls to fidelity.com.

## Usage

```python
from datetime import date
from fidelity_helper import Fidelity

# In this example the callback assumes page.evaluate is provided by your browser
# automation framework.
fidelity = Fidelity(lambda expr: page.evaluate(expr, await_promise=True))

# Get transactions for specific accounts and date range
transactions = await fidelity.get_transactions(
    accounts=["123456789", "987654321"], start=date(2024, 1, 1), end=date(2024, 1, 31)
)

for t in transactions:
    print(f"{t.date}\t${t.amount}\t{t.description}")
```
See [fidelity_example.py](https://github.com/righteffort/finance-helper/python/fidelity-example/fidelity_example.py) for a working example.
"""  # noqa: E501

from .fidelity import Account, Fidelity, FidelityError, Transaction


__all__ = ["Transaction", "Account", "Fidelity", "FidelityError"]  # noqa: RUF022
