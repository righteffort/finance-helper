// Response model interfaces matching Python Pydantic models

export interface AcctDetailModel {
  acctNum: string;
  acctType: string;
  name: string;
}

export interface SearchCriteriaDetailModel {
  timePeriod: number;
  txnCat: null;
  viewType: string;
  histSortDir: string;
  acctHistSort: string;
  hasBasketName: boolean;
  txnFromDate: string;
  txnToDate: string;
}

export interface GetTransactionsReqVarsModel {
  isNewOrderApi: boolean;
  isSupportCrypto: boolean;
  hideDCOrders: boolean;
  acctIdList: string;
  acctDetailList: AcctDetailModel[];
  searchCriteriaDetail: SearchCriteriaDetailModel;
}

export interface GetTransactionsReqModel {
  operationName: string;
  variables: GetTransactionsReqVarsModel;
  query: string;
}

export interface GetTransactionsRespHistoryModel {
  acctNum: string;
  amount: string;
  date: string;
  description: string;
  intradayInd: boolean;
  orderNumber: string;
}

export interface GetTransactionsRespTransactionsModel {
  historys: GetTransactionsRespHistoryModel[];
}

export interface GetTransactionsRespDataModel {
  getTransactions: GetTransactionsRespTransactionsModel;
}

export interface GetTransactionsRespModel {
  data: GetTransactionsRespDataModel;
}

export interface BackendStatusModel {
  account: string;
}

export interface SysStatusModel {
  backend: BackendStatusModel;
}

export interface PreferenceDetailModel {
  name: string;
}

export interface GetAccountsRespAcctDetailModel {
  acctNum: string;
  acctType: string;
  preferenceDetail: PreferenceDetailModel;
}

export interface PersonModel {
  assets: GetAccountsRespAcctDetailModel[];
}

export interface GetAccountsContextModel {
  sysStatus: SysStatusModel;
  person: PersonModel;
}

export interface GetAccountsRespDataModel {
  getContext: GetAccountsContextModel;
}

export interface GetAccountsRespModel {
  data: GetAccountsRespDataModel;
}

export interface GetTransactionsFetchOptionsPartial {
  body: string; // JSON string representation of GetTransactionsReqModel
  [key: string]: unknown;
}
