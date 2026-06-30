import api from './index'

export const getPayments = (params) => api.get('/payments', { params })
export const getPayment = (id) => api.get(`/payments/${id}`)
export const createPayment = (data) => api.post('/payments', data)
export const reversePayment = (id) => api.post(`/payments/${id}/reverse`)

export default {
  getPayments, getPayment, createPayment, reversePayment
}
