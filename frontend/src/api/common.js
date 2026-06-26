import api from './index'
import accountsApi from './accounts'
import exportApi from './export'
import uploadApi from './upload'
import backupApi from './backup'

let _enumsCache = null
export const getEnums = async () => {
  if (_enumsCache) return _enumsCache
  const data = await api.get('/enums')
  _enumsCache = data
  return data
}

export const getLogs = (params) => api.get('/logs', { params })

export const getReconciliations = (params) => api.get('/reconciliations', { params })
export const getReconciliationDetail = (params) => api.get('/reconciliations/detail', { params })

export { getAccounts, updateAccount, createAccount, deleteAccount } from './accounts'
export { getExportUrl, exportFile, exportProductsBatch } from './export'
export { uploadImage, replaceImage, deleteImage } from './upload'
export { hotBackup, listBackups, getBackupDownloadUrl } from './backup'

export default {
  getEnums, getLogs, getReconciliations, getReconciliationDetail,
  ...accountsApi, ...exportApi, ...uploadApi, ...backupApi
}
