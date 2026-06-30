import api from './index'

// Purchases
export const getPurchases = (params) => api.get('/purchases', { params })
export const createPurchase = (data) => api.post('/purchases', data)
export const updatePurchase = (id, data) => api.put(`/purchases/${id}`, data)
export const deletePurchase = (id) => api.delete(`/purchases/${id}`)

// Sales
export const getSales = (params) => api.get('/sales', { params })
export const getSale = (id) => api.get(`/sales/${id}`)
export const createSale = (data) => api.post('/sales', data)
export const updateSale = (id, data) => api.put(`/sales/${id}`, data)
export const deleteSale = (id) => api.delete(`/sales/${id}`)
export const cancelSale = (id) => api.post(`/sales/${id}/cancel`)
export const returnSale = (id, data) => api.post(`/sales/${id}/return`, data)

// Purchases - cancel/return
export const cancelPurchase = (id) => api.post(`/purchases/${id}/cancel`)
export const returnPurchase = (id, data) => api.post(`/purchases/${id}/return`, data)

export default {
  getPurchases, createPurchase, updatePurchase, deletePurchase,
  cancelPurchase, returnPurchase,
  getSales, getSale, createSale, updateSale, deleteSale,
  cancelSale, returnSale
}