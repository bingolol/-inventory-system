import api, { baseURL } from './index'

export const hotBackup = () => api.post('/backup/hot')
export const listBackups = () => api.get('/backup/list')
export const getBackupDownloadUrl = (filename) => `${baseURL}/backup/download/${filename}`

export default { hotBackup, listBackups, getBackupDownloadUrl }
