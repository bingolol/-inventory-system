import api from './index'

// Expenses
export const getExpenses = (params) => api.get('/expenses', { params })
export const createExpense = (data) => api.post('/expenses', data)
export const updateExpense = (id, data) => api.put(`/expenses/${id}`, data)
export const deleteExpense = (id) => api.delete(`/expenses/${id}`)
export const reverseExpense = (id) => api.post(`/expenses/${id}/reverse`)

export default {
  getExpenses, createExpense, updateExpense, deleteExpense,
  reverseExpense
}