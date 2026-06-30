import api from './index'

export const getReceipts = (params) => api.get('/receipts', { params })
export const getReceipt = (id) => api.get(`/receipts/${id}`)
export const createReceipt = (data) => api.post('/receipts', data)
export const reverseReceipt = (id) => api.post(`/receipts/${id}/reverse`)

export default {
  getReceipts, getReceipt, createReceipt, reverseReceipt
}
