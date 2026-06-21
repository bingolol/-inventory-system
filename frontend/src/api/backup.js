import api from './index'

export const hotBackup = () => api.post('/backup/hot')
export const listBackups = () => api.get('/backup/list')
export const getBackupDownloadUrl = (filename) => `/api/backup/download/${filename}`

export default { hotBackup, listBackups, getBackupDownloadUrl }
