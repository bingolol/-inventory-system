import api from './index'

// Utility: format money value (handles string/number/null/undefined)
export const formatMoney = (value) => {
  if (value === null || value === undefined || value === '') return '0.00'
  const num = Number(value)
  if (isNaN(num)) return '0.00'
  // 千分位显示，保留2位小数
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// Enums (带内存缓存，首次调用请求API，后续直接返回缓存)
let _enumsCache = null
export const getEnums = async () => {
  if (_enumsCache) return _enumsCache
  const data = await api.get('/enums')
  _enumsCache = data
  return data
}

// Accounts
export const getAccounts = () => api.get('/accounts')
export const updateAccount = (id, data) => api.put(`/accounts/${id}`, data)
export const createAccount = (data) => api.post('/accounts', data)
export const deleteAccount = (id) => api.delete(`/accounts/${id}`)

// Export
export const getExportUrl = (type, format = 'excel', params = {}) => {
  const query = new URLSearchParams({ format, ...params }).toString()
  return `/api/export/${type}?${query}`
}

export const exportFile = async (type, format = 'excel', params = {}) => {
  const res = await api.get(`/export/${type}`, {
    params: { format, ...params },
    responseType: 'blob'
  })
  const blob = res.data
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
}

export const exportProductsBatch = async (productIds, format = 'excel') => {
  const res = await api.get('/export/products-batch', {
    params: { product_ids: productIds.join(','), format },
    responseType: 'blob'
  })
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
}

// Image Upload
export const uploadImage = (formData, businessType = 'expense', recordId = 0) => {
  formData.append('business_type', businessType)
  formData.append('record_id', recordId)
  return api.post('/upload/image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000
  })
}
export const replaceImage = (formData, businessType, recordId, oldImageUrl) => {
  formData.append('business_type', businessType)
  formData.append('record_id', recordId)
  formData.append('old_image_url', oldImageUrl)
  return api.put('/upload/image', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 30000
  })
}
export const deleteImage = (imageUrl) => api.delete('/upload/image', { params: { image_url: imageUrl } })

// Backup
export const hotBackup = () => api.post('/backup/hot')
export const listBackups = () => api.get('/backup/list')
export const getBackupDownloadUrl = (filename) => `/api/backup/download/${filename}`

// Logs
export const getLogs = (params) => api.get('/logs', { params })

// Reconciliations (对账)
export const getReconciliations = (params) => api.get('/reconciliations', { params })
export const getReconciliationDetail = (params) => api.get('/reconciliations/detail', { params })

export default {
  getEnums, getAccounts, updateAccount, createAccount, deleteAccount,
  getExportUrl, exportFile, exportProductsBatch,
  uploadImage, replaceImage, deleteImage,
  hotBackup, listBackups, getBackupDownloadUrl,
  getLogs,
  getReconciliations, getReconciliationDetail,
  formatMoney
}