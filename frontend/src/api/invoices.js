import api from './index'

// Invoices
export const getInvoices = (params) => api.get('/invoices', { params })
export const createInvoice = (data) => api.post('/invoices', data)
export const updateInvoice = (id, data) => api.put(`/invoices/${id}`, data)
export const deleteInvoice = (id) => api.delete(`/invoices/${id}`)
export const certifyInvoice = (id) => api.post(`/invoices/${id}/certify`)
export const reverseInvoice = (id, reason) => api.post(`/invoices/${id}/reverse`, null, { params: { reason } })

// Tax Report
export const getTaxReport = (year, quarter) => api.get('/tax-report', { params: { year, quarter } })
export const getIncomeTaxReport = (year, quarter) => api.get('/income-tax-report', { params: { year, quarter } })
export const getTaxReportMonthly = (year, month) => api.get('/tax-report/monthly', { params: { year, month } })

export default {
  getInvoices, createInvoice, updateInvoice, deleteInvoice, certifyInvoice, reverseInvoice,
  getTaxReport, getIncomeTaxReport, getTaxReportMonthly
}