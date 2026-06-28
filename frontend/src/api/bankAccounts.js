import api from './index'

export const getBankAccounts = () => api.get('/bank-accounts')
export const createBankAccount = (data) => api.post('/bank-accounts', data)
export const updateBankAccount = (id, data) => api.put(`/bank-accounts/${id}`, data)
export const deleteBankAccount = (id) => api.delete(`/bank-accounts/${id}`)

export default { getBankAccounts, createBankAccount, updateBankAccount, deleteBankAccount }
