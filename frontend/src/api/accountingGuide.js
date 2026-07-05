import api from './index'

export const getAccountingGuide = (year, quarter) => api.get('/accounting-guide', { params: { year, quarter } })

export default { getAccountingGuide }
