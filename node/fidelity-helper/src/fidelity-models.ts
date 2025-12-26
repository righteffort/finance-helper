export interface GetTransactionsReqModel {
  operationName: string;
  variables: {
    isNewOrderApi: boolean;
    isSupportCrypto: boolean;
    hideDCOrders: boolean;
    acctIdList: string;
    acctDetailList: {
      acctNum: string;
      acctType: string;
      name: string;
    }[];
    searchCriteriaDetail: {
      timePeriod: number;
      txnCat: null;
      viewType: string;
      histSortDir: string;
      acctHistSort: string;
      hasBasketName: boolean;
      txnFromDate: string;
      txnToDate: string;
    };
  };
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

export interface GetTransactionsRespModel {
  data: {
    getTransactions: {
      historys: GetTransactionsRespHistoryModel[];
    };
  };
}

export interface GetAccountsRespModel {
  data: {
    getContext: {
      sysStatus: {
        backend: {
          account: string;
        };
      };
      person: {
        assets: {
          acctNum: string;
          acctType: string;
          preferenceDetail: {
            name: string;
          };
        }[];
      };
    };
  };
}
