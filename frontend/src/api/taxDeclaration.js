import api from './index'

export const getPendingDeclarations = () => api.get('/tax/pending-declarations')

export const getDeclarations = () => api.get('/tax/declarations')

export const declareVAT = (period, taxpayerType) => api.post('/tax/declare', { period, taxpayer_type: taxpayerType })

export const declareSurcharge = (period, data) => api.post('/tax/surcharge-declaration', {
  period,
  urban_construction_tax: data.urban_construction_tax,
  education_surcharge: data.education_surcharge,
  local_education_surcharge: data.local_education_surcharge,
  notes: data.notes || '',
})

export default { getPendingDeclarations, getDeclarations, declareVAT, declareSurcharge }