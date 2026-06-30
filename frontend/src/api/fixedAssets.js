import api from './index'

export const getFixedAssets = (params) => api.get('/fixed-assets', { params })
export const createFixedAsset = (data) => api.post('/fixed-assets', data)
export const updateFixedAsset = (id, data) => api.put(`/fixed-assets/${id}`, data)
export const deleteFixedAsset = (id) => api.delete(`/fixed-assets/${id}`)
export const disposeFixedAsset = (id, disposalPrice, disposalDate) => api.post(`/fixed-assets/${id}/dispose`, null, { params: { disposal_price: disposalPrice, disposal_date: disposalDate } })
export const depreciateFixedAsset = (id, period) => api.post(`/fixed-assets/${id}/depreciate`, null, { params: { period } })
export const batchDepreciateFixedAssets = (period) => api.post('/fixed-assets/batch-depreciate', null, { params: { period } })

export default {
  getFixedAssets, createFixedAsset, updateFixedAsset, deleteFixedAsset, disposeFixedAsset,
  depreciateFixedAsset, batchDepreciateFixedAssets
}
