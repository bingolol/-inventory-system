import api from './index'

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

export default { uploadImage, replaceImage, deleteImage }
