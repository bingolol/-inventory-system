import api from './index'

// Reports (业务报表)
export const getOverview = () => api.get('/reports/overview')
export const getPurchaseReport = (params) => api.get('/reports/purchase', { params })
export const getSaleReport = (params) => api.get('/reports/sale', { params })
export const getProfitReport = (params) => api.get('/reports/profit', { params })
export const getTrend = (params) => api.get('/reports/trend', { params })

// Financial Reports (财务报表)
export const getBalanceSheet = (date) => api.get('/financial-reports/balance-sheet', { params: { date } })
export const getIncomeStatement = (startDate, endDate) => api.get('/financial-reports/income-statement', { params: { start_date: startDate, end_date: endDate } })
export const getFinancialSummary = (date) => api.get('/financial-reports/financial-summary', { params: { date } })
export const getCWBBXQYKJZZ = (reportType, date) => api.get('/financial-reports/cwbb-xqykjzz', { params: { report_type: reportType, date } })

// Cash Flows
export const getCashFlowStatement = (startDate, endDate) => api.get('/cash-flows/statement', { params: { start_date: startDate, end_date: endDate } })
export const getCashFlowTransactions = (params) => api.get('/cash-flows/transactions', { params })
export const createCashFlowTransaction = (data) => api.post('/cash-flows/transactions', data)
export const updateCashFlowTransaction = (id, data) => api.put(`/cash-flows/transactions/${id}`, data)
export const deleteCashFlowTransaction = (id) => api.delete(`/cash-flows/transactions/${id}`)
export const reverseCashFlowTransaction = (id) => api.post(`/cash-flows/transactions/${id}/reverse`)

// Month Close
export const monthClose = (period) => api.post('/finance/month-close', { period })

// Opening Balance
export const getOpeningBalances = () => api.get('/opening-balances')
export const getOpeningBalance = (id) => api.get(`/opening-balances/${id}`)
export const createOpeningBalance = (data) => api.post('/opening-balances', data)
export const updateOpeningBalance = (id, data) => api.put(`/opening-balances/${id}`, data)
export const deleteOpeningBalance = (id) => api.delete(`/opening-balances/${id}`)
export const getLatestOpeningBalance = () => api.get('/opening-balances/latest')

// Finance Query (财务查询 API - Phase 3)
export const getTrialBalance = (params) => api.get('/finance/reports/trial-balance', { params })
export const getAccountChart = () => api.get('/finance/accounts/chart')
export const getJournalMoves = (params) => api.get('/finance/journal/moves', { params })
export const getJournalMove = (id) => api.get(`/finance/journal/moves/${id}`)
export const getPartnerReceivable = (partnerId, params) => api.get(`/finance/receivable/partner/${partnerId}`, { params })

export default {
  getOverview, getPurchaseReport, getSaleReport, getProfitReport, getTrend,
  getBalanceSheet, getIncomeStatement, getFinancialSummary, getCWBBXQYKJZZ,
  getCashFlowStatement, getCashFlowTransactions, createCashFlowTransaction, updateCashFlowTransaction, deleteCashFlowTransaction,
  getOpeningBalances, getOpeningBalance, createOpeningBalance, updateOpeningBalance, deleteOpeningBalance, getLatestOpeningBalance,
  getTrialBalance, getAccountChart, getJournalMoves, getJournalMove, getPartnerReceivable,
  reverseCashFlowTransaction, monthClose
}