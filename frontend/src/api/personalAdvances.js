import api from './index'

// 其他应付款/个人垫付
export const getPersonalAdvances = (params) => api.get('/personal-advances', { params })
export const getPersonalAdvance = (id) => api.get(`/personal-advances/${id}`)
export const getPersonalAdvanceTotals = () => api.get('/personal-advances/totals')
export const getPersonalAdvanceSummary = () => api.get('/personal-advances/summary')
export const createPersonalAdvance = (data) => api.post('/personal-advances', data)
export const repayPersonalAdvance = (id, data) => api.post(`/personal-advances/${id}/repay`, data)
export const reversePersonalAdvance = (id) => api.post(`/personal-advances/${id}/reverse`)
export const listPersonalAdvanceRepayments = (id) => api.get(`/personal-advances/${id}/repayments`)
export const reversePersonalAdvanceRepayment = (advanceId, repaymentId) =>
  api.post(`/personal-advances/${advanceId}/repayments/${repaymentId}/reverse`)

export default {
  getPersonalAdvances,
  getPersonalAdvance,
  getPersonalAdvanceTotals,
  getPersonalAdvanceSummary,
  createPersonalAdvance,
  repayPersonalAdvance,
  reversePersonalAdvance,
  listPersonalAdvanceRepayments,
  reversePersonalAdvanceRepayment,
}
