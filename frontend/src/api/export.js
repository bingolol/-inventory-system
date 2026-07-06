import api, { baseURL } from './index'

export const getExportUrl = (type, format = 'excel', params = {}) => {
  const query = new URLSearchParams({ format, ...params }).toString()
  return `${baseURL}/export/${type}?${query}`
}

/**
 * 通用导出下载（blob → 文件）
 */
const downloadBlob = (blob, fallbackName, format, disposition) => {
  let filename = fallbackName
  if (disposition) {
    const match = disposition.match(/filename\*=UTF-8''(.+)/i)
    if (match) filename = decodeURIComponent(match[1])
  }
  let mime = 'application/octet-stream'
  if (format === 'csv') {
    mime = 'text/csv'
  } else if (filename.endsWith('.xls')) {
    mime = 'application/vnd.ms-excel'
  } else if (filename.endsWith('.xlsx')) {
    mime = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  }
  const url = window.URL.createObjectURL(new Blob([blob], { type: mime }))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', filename)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

export const exportFile = async (type, format = 'excel', params = {}) => {
  const res = await api.get(`/export/${type}`, {
    params: { format, ...params },
    responseType: 'blob'
  })
  const disposition = res.headers['content-disposition']
  downloadBlob(res.data, `${type}.${format === 'csv' ? 'csv' : 'xlsx'}`, format, disposition)
  return true
}

export const exportProductsBatch = async (productIds, format = 'excel') => {
  const res = await api.get('/export/products-batch', {
    params: { product_ids: productIds.join(','), format },
    responseType: 'blob'
  })
  const ext = format === 'csv' ? 'csv' : 'xlsx'
  downloadBlob(res.data, `库存商品导出_${productIds.length}条.${ext}`, format, null)
  return true
}

export const exportCWBBXQYKJZZ = async (reportType, date) => {
  const res = await api.get('/export/cwbb-xqykjzz', {
    params: { report_type: reportType, date },
    responseType: 'blob'
  })
  downloadBlob(res.data, `财务报表_${reportType}_${date}.xls`, 'excel', res.headers['content-disposition'])
  return true
}

export default { getExportUrl, exportFile, exportProductsBatch, exportCWBBXQYKJZZ }
