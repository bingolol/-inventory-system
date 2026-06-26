import api from './index'

export const getFixedAssets = (params) => api.get('/fixed-assets', { params })
export const createFixedAsset = (data) => api.post('/fixed-assets', data)
export const updateFixedAsset = (id, data) => api.put(`/fixed-assets/${id}`, data)
export const deleteFixedAsset = (id) => api.delete(`/fixed-assets/${id}`)
export const disposeFixedAsset = (id, reason) => api.post(`/fixed-assets/${id}/dispose`, null, { params: { reason } })

export default {
  getFixedAssets, createFixedAsset, updateFixedAsset, deleteFixedAsset, disposeFixedAsset
}
