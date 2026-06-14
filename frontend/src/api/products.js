import api from './index'

// Products
export const getProducts = (params) => api.get('/products', { params })
export const getProduct = (id) => api.get(`/products/${id}`)
export const createProduct = (data) => api.post('/products', data)
export const updateProduct = (id, data) => api.put(`/products/${id}`, data)
export const deleteProduct = (id) => api.delete(`/products/${id}`)
export const getCategories = () => api.get('/products/categories/list')

// Inventory
export const getInventory = (params) => api.get('/inventory', { params })
export const getAlerts = () => api.get('/inventory/alerts')
export const adjustInventory = (productId, data) => api.put(`/inventory/${productId}`, data)

export default {
  getProducts, getProduct, createProduct, updateProduct, deleteProduct, getCategories,
  getInventory, getAlerts, adjustInventory
}