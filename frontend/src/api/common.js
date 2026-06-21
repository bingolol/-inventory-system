import api from './index'
import { formatMoney } from '../utils/format'
import accountsApi from './accounts'
import exportApi from './export'
import uploadApi from './upload'
import backupApi from './backup'

// formatMoney 已迁移至 utils/format.js，此处重导出保持兼容
export { formatMoney } from '../utils/format'

// Enums (带内存缓存，首次调用请求API，后续直接返回缓存)
let _enumsCache = null
export const getEnums = async () => {
  if (_enumsCache) return _enumsCache
  const data = await api.get('/enums')
  _enumsCache = data
  return data
}

// Logs
export const getLogs = (params) => api.get('/logs', { params })

// Reconciliations (对账)
export const getReconciliations = (params) => api.get('/reconciliations', { params })
export const getReconciliationDetail = (params) => api.get('/reconciliations/detail', { params })

// 已拆分的模块 - 重导出保持向后兼容
export { getAccounts, updateAccount, createAccount, deleteAccount } from './accounts'
export { getExportUrl, exportFile, exportProductsBatch } from './export'
export { uploadImage, replaceImage, deleteImage } from './upload'
export { hotBackup, listBackups, getBackupDownloadUrl } from './backup'

export default {
  getEnums, getLogs, getReconciliations, getReconciliationDetail,
  ...accountsApi, ...exportApi, ...uploadApi, ...backupApi,
  formatMoney
}
