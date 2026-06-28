import api from './index'

export const getBankTransactions = (bankAccountId, params) =>
  api.get('/bank-transactions', { params: { bank_account_id: bankAccountId, ...params } })

export const createBankTransaction = (data) => api.post('/bank-transactions', data)

export default { getBankTransactions, createBankTransaction }
