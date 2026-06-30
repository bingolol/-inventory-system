import api from './index'

export const importBankStatement = (data) => api.post('/bank/statement', data)
export const getBankStatement = (id) => api.get(`/bank/statement/${id}`)
export const reconcileBank = (period) => api.post('/bank/reconcile', null, { params: { period } })
export const getReconciliation = (period) => api.get('/bank/reconciliation', { params: { period } })
export const confirmReconciliation = (id) => api.post(`/bank/reconciliation/${id}/confirm`)
export const generateReconciliationEntry = (id) => api.post(`/bank/reconciliation/${id}/generate-entry`)
export const forceMatch = (id, data) => api.post(`/bank/reconciliation/${id}/match`, data)
export const createBankEntry = (data) => api.post('/bank/entry', data)

export default {
  importBankStatement, getBankStatement, reconcileBank, getReconciliation,
  confirmReconciliation, generateReconciliationEntry, forceMatch, createBankEntry
}
