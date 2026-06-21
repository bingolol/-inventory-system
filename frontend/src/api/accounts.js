import api from './index'

export const getAccounts = () => api.get('/accounts')
export const updateAccount = (id, data) => api.put(`/accounts/${id}`, data)
export const createAccount = (data) => api.post('/accounts', data)
export const deleteAccount = (id) => api.delete(`/accounts/${id}`)

export default { getAccounts, updateAccount, createAccount, deleteAccount }
