import api from './index'

// Personal Transactions
export const getPersonalSummary = () => api.get('/personal/summary')
export const getPersonalTransactions = (params) => api.get('/personal', { params })
export const getPersonalCategorySummary = (params) => api.get('/personal/category_summary', { params })
export const getPersonalMonthlySummary = (params) => api.get('/personal/monthly_summary', { params })
export const createPersonalTransaction = (data) => api.post('/personal', data)
export const updatePersonalTransaction = (id, data) => api.put(`/personal/${id}`, data)
export const deletePersonalTransaction = (id) => api.delete(`/personal/${id}`)

export default {
  getPersonalSummary, getPersonalTransactions, getPersonalCategorySummary, getPersonalMonthlySummary,
  createPersonalTransaction, updatePersonalTransaction, deletePersonalTransaction
}