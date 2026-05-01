import axios from 'axios'

// 优先使用 Vite 环境变量，开发环境走 proxy，生产环境走绝对路径
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''
const baseURL = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}/api`
  : '/api'

const api = axios.create({
  baseURL,
  timeout: 10000
})

// 导出baseURL供组件使用
export { API_BASE_URL }

// 统一处理image_url：相对路径→完整URL
export const resolveImageUrl = (url) => {
  if (!url) return ''
  if (url.startsWith('http')) return url
  return `${API_BASE_URL}${url}`
}

// 从 localStorage 读取当前账本ID，每个请求自动带上
// 如果没有设置，则默认使用账本1（日运办公）
api.interceptors.request.use(config => {
  let accountId = '1' // 默认使用账本1（日运办公）
  try {
    const stored = localStorage.getItem('currentAccountId')
    if (stored) {
      accountId = stored
    } else {
      localStorage.setItem('currentAccountId', accountId)
    }
  } catch (e) {
    // localStorage 不可用（隐私模式、跨域限制等），使用默认值
    console.warn('[API] localStorage 不可用，使用默认 accountId:', accountId)
  }
  config.headers['X-Account-ID'] = accountId
  config.headers['X-Operator'] = 'user'
  return config
})

api.interceptors.response.use(
  res => {
    // blob 请求返回完整响应对象，让调用方通过 res.data 获取 Blob
    if (res.config.responseType === 'blob') {
      return res
    }
    return res.data
  },
  err => {
    console.error('API Error:', err.response?.data || err.message)
    return Promise.reject(err)
  }
)

export default {
  // Enums (带内存缓存，首次调用请求API，后续直接返回缓存)
  _enumsCache: null,
  getEnums: async function () {
    if (this._enumsCache) return this._enumsCache
    const data = await api.get('/enums')
    this._enumsCache = data
    return data
  },

  // Accounts
  getAccounts: () => api.get('/accounts'),

  // Products
  getProducts: (params) => api.get('/products/', { params }),
  getProduct: (id) => api.get(`/products/${id}`),
  createProduct: (data) => api.post('/products/', data),
  updateProduct: (id, data) => api.put(`/products/${id}`, data),
  deleteProduct: (id) => api.delete(`/products/${id}`),
  getCategories: () => api.get('/products/categories/list'),

  // Suppliers
  getSuppliers: (params) => api.get('/suppliers/', { params }),
  createSupplier: (data) => api.post('/suppliers/', data),
  updateSupplier: (id, data) => api.put(`/suppliers/${id}`, data),
  deleteSupplier: (id) => api.delete(`/suppliers/${id}`),

  // Customers
  getCustomers: (params) => api.get('/customers/', { params }),
  createCustomer: (data) => api.post('/customers/', data),
  updateCustomer: (id, data) => api.put(`/customers/${id}`, data),
  deleteCustomer: (id) => api.delete(`/customers/${id}`),

  // Purchases
  getPurchases: (params) => api.get('/purchases/', { params }),
  createPurchase: (data) => api.post('/purchases/', data),
  updatePurchase: (id, data) => api.put(`/purchases/${id}`, data),
  deletePurchase: (id) => api.delete(`/purchases/${id}`),

  // Sales
  getSales: (params) => api.get('/sales/', { params }),
  getSale: (id) => api.get(`/sales/${id}`),
  createSale: (data) => api.post('/sales/', data),
  updateSale: (id, data) => api.put(`/sales/${id}`, data),
  deleteSale: (id) => api.delete(`/sales/${id}`),

  // Inventory
  getInventory: (params) => api.get('/inventory/', { params }),
  getAlerts: () => api.get('/inventory/alerts'),
  adjustInventory: (productId, data) => api.put(`/inventory/${productId}`, data),

  // Reports
  getOverview: () => api.get('/reports/overview'),
  getPurchaseReport: (params) => api.get('/reports/purchase', { params }),
  getSaleReport: (params) => api.get('/reports/sale', { params }),
  getProfitReport: (params) => api.get('/reports/profit', { params }),
  getTrend: (params) => api.get('/reports/trend', { params }),

  // Personal Transactions
  getPersonalSummary: () => api.get('/personal/summary'),
  getPersonalTransactions: (params) => api.get('/personal/', { params }),
getPersonalCategorySummary: (params) => api.get('/personal/category_summary', { params }),
getPersonalMonthlySummary: (params) => api.get('/personal/monthly_summary', { params }),
  createPersonalTransaction: (data) => api.post('/personal/', data),
  updatePersonalTransaction: (id, data) => api.put(`/personal/${id}`, data),
  deletePersonalTransaction: (id) => api.delete(`/personal/${id}`),

  // Operation Logs
  getLogs: (params) => api.get('/logs/', { params }),

  // Invoices
  getInvoices: (params) => api.get('/invoices/', { params }),
  createInvoice: (data) => api.post('/invoices/', data),
  updateInvoice: (id, data) => api.put(`/invoices/${id}`, data),
  deleteInvoice: (id) => api.delete(`/invoices/${id}`),
  certifyInvoice: (id) => api.post(`/invoices/${id}/certify`),

  // Tax Report
  getTaxReport: (year, quarter) => api.get('/tax-report/', { params: { year, quarter } }),
  getIncomeTaxReport: (year) => api.get('/income-tax-report/', { params: { year } }),

  // Expenses
  getExpenses: (params) => api.get('/expenses/', { params }),
  createExpense: (data) => api.post('/expenses/', data),
  updateExpense: (id, data) => api.put(`/expenses/${id}`, data),
  deleteExpense: (id) => api.delete(`/expenses/${id}`),

  // Projects
  getProjects: (params) => api.get('/projects/', { params }),
  getProjectList: (params) => api.get('/projects/list', { params }),
  getProjectDetails: (projectName) => api.get(`/projects/${projectName}/details`),
  getProjectDetail: (id) => api.get(`/projects/${id}/cost-income`),
  createProject: (data) => api.post('/projects/', data),
  updateProject: (id, data) => api.put(`/projects/manage/${id}`, data),
  deleteProject: (id) => api.delete(`/projects/manage/${id}`),
  getProjectCosts: (params) => api.get('/costs/', { params }),
  createProjectCost: (data) => api.post('/costs/', data),
  updateProjectCost: (id, data) => api.put(`/costs/${id}`, data),
  deleteProjectCost: (id) => api.delete(`/costs/${id}`),
  getProjectIncomes: (params) => api.get('/costs/incomes/', { params }),
  createProjectIncome: (data) => api.post('/costs/incomes/', data),
  updateProjectIncome: (id, data) => api.put(`/costs/incomes/${id}`, data),
  deleteProjectIncome: (id) => api.delete(`/costs/incomes/${id}`),

  // Export
  getExportUrl: (type, format = 'excel', params = {}) => {
    const query = new URLSearchParams({ format, ...params }).toString()
    return `/api/export/${type}?${query}`
  },
  // 通用导出：通过 axios 发请求（自动携带 X-Account-ID），blob 响应触发浏览器下载
  exportFile: async (type, format = 'excel', params = {}) => {
    const res = await api.get(`/export/${type}`, {
      params: { format, ...params },
      responseType: 'blob'
    })
    // 拦截器对 blob 请求返回完整 AxiosResponse
    const blob = res.data
    // 从 Content-Disposition 解析文件名，fallback 用 type
    let filename = `${type}.${format === 'csv' ? 'csv' : 'xlsx'}`
    const disposition = res.headers['content-disposition']
    if (disposition) {
      const match = disposition.match(/filename\*=UTF-8''(.+)/i)
      if (match) filename = decodeURIComponent(match[1])
    }
    const ext = format === 'csv' ? 'csv' : 'xlsx'
    const mime = format === 'csv'
      ? 'text/csv'
      : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    const url = window.URL.createObjectURL(new Blob([blob], { type: mime }))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', filename)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    return true
  },
  // 批量导出商品（通过 api 实例发起请求，自动携带 X-Account-ID，blob 响应在拦截器中返回完整响应对象）
  exportProductsBatch: async (productIds, format = 'excel') => {
    const res = await api.get('/export/products-batch', {
      params: { product_ids: productIds.join(','), format },
      responseType: 'blob'
    })

    // 拦截器对 blob 请求返回完整 AxiosResponse，res.data 是 Blob
    const blob = res.data
    const ext = format === 'csv' ? 'csv' : 'xlsx'
    const mime = format === 'csv'
      ? 'text/csv'
      : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    const url = window.URL.createObjectURL(new Blob([blob], { type: mime }))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `库存商品导出_${productIds.length}条.${ext}`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    return true
  },

  // Opening Balance
  getOpeningBalances: () => api.get('/opening-balances/'),
  getOpeningBalance: (id) => api.get(`/opening-balances/${id}`),
  createOpeningBalance: (data) => api.post('/opening-balances/', data),
  updateOpeningBalance: (id, data) => api.put(`/opening-balances/${id}`, data),
  deleteOpeningBalance: (id) => api.delete(`/opening-balances/${id}`),
  getLatestOpeningBalance: () => api.get('/opening-balances/latest'),

  // Financial Reports
  getBalanceSheet: (date) => api.get('/financial-reports/balance-sheet', { params: { date } }),
  getIncomeStatement: (startDate, endDate) => api.get('/financial-reports/income-statement', { params: { start_date: startDate, end_date: endDate } }),
  getFinancialSummary: (date) => api.get('/financial-reports/financial-summary', { params: { date } }),

  // Tax Report (Monthly)
  getTaxReportMonthly: (year, month) => api.get('/tax-report/monthly', { params: { year, month } }),

  // Cash Flows
  getCashFlowStatement: (startDate, endDate) => api.get('/cash-flows/statement', { params: { start_date: startDate, end_date: endDate } }),
  getCashFlowTransactions: (params) => api.get('/cash-flows/transactions', { params }),
  createCashFlowTransaction: (data) => api.post('/cash-flows/transactions', data),
  updateCashFlowTransaction: (id, data) => api.put(`/cash-flows/transactions/${id}`, data),
  deleteCashFlowTransaction: (id) => api.delete(`/cash-flows/transactions/${id}`),

  // Image Upload
  uploadImage: (formData, businessType = 'expense', recordId = 0) => {
    formData.append('business_type', businessType)
    formData.append('record_id', recordId)
    return api.post('/upload/image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 30000
    })
  },
  replaceImage: (formData, businessType, recordId, oldImageUrl) => {
    formData.append('business_type', businessType)
    formData.append('record_id', recordId)
    formData.append('old_image_url', oldImageUrl)
    return api.put('/upload/image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 30000
    })
  },
  deleteImage: (imageUrl) => api.delete('/upload/image', { params: { image_url: imageUrl } }),

  // Backup
  hotBackup: () => api.post('/backup/hot'),
  listBackups: () => api.get('/backup/list'),
  getBackupDownloadUrl: (filename) => `/api/backup/download/${filename}`,

  // Reconciliations (对账)
  getReconciliations: (params) => api.get('/reconciliation/', { params }),
  getReconciliationDetail: (params) => api.get('/reconciliation/detail/', { params }),
}