"""Fidelity request and response objects. Use with caution."""

# ruff: noqa: N815  # mixed-case-variable-in-class-scope
# ruff: noqa: D101  # Missing docstring in public class

from pydantic import BaseModel, ConfigDict


class AcctDetailModel(BaseModel):
    acctNum: str
    acctType: str
    name: str


class SearchCriteriaDetailModel(BaseModel):
    timePeriod: int
    txnCat: None
    viewType: str
    histSortDir: str
    acctHistSort: str
    hasBasketName: bool
    txnFromDate: str
    txnToDate: str


class GetTransactionsReqVarsModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    isNewOrderApi: bool
    isSupportCrypto: bool
    hideDCOrders: bool
    acctIdList: str
    acctDetailList: list[AcctDetailModel]
    searchCriteriaDetail: SearchCriteriaDetailModel


class GetTransactionsReqModel(BaseModel):
    """Fidelity get_transactions request."""

    model_config = ConfigDict(extra="forbid", strict=True)
    operationName: str
    variables: GetTransactionsReqVarsModel
    query: str


class GetTransactionsRespHistoryModel(BaseModel):
    """Single transaction in Fidelity response to get_transactions."""

    acctNum: str
    amount: str
    date: str
    description: str
    intradayInd: bool
    orderNumber: str | None


class GetTransactionsRespTransactionsModel(BaseModel):
    historys: list[GetTransactionsRespHistoryModel]


class GetTransactionsRespDataModel(BaseModel):
    getTransactions: GetTransactionsRespTransactionsModel


class GetTransactionsRespModel(BaseModel):
    """Fidelity response to get_transactions."""

    data: GetTransactionsRespDataModel


class BackendStatusModel(BaseModel):
    account: str


class SysStatusModel(BaseModel):
    backend: BackendStatusModel


class PreferenceDetailModel(BaseModel):
    name: str


class GetAccountsRespAcctDetailModel(BaseModel):
    acctNum: str
    acctType: str
    preferenceDetail: PreferenceDetailModel


class PersonModel(BaseModel):
    assets: list[GetAccountsRespAcctDetailModel]


class GetAccountsContextModel(BaseModel):
    sysStatus: SysStatusModel
    person: PersonModel


class GetAccountsRespDataModel(BaseModel):
    getContext: GetAccountsContextModel


class GetAccountsRespModel(BaseModel):
    """Fidelity response to get_accounts."""

    data: GetAccountsRespDataModel
