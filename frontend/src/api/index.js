import axios from 'axios'
import { useAccountStore } from '../stores/account'
import { useAuthStore } from '../stores/auth'
import { handleError } from '../utils/errorHandler'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''
const baseURL = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}/api`
  : '/api'

const api = axios.create({
  baseURL,
  timeout: 10000
})

export { API_BASE_URL, handleError }

export const resolveImageUrl = (url) => {
  if (!url) return ''
  if (url.startsWith('http')) return url
  return `${API_BASE_URL}${url}`
}

let _isRefreshing = false
let _pendingRequests = []

function _onRefreshed(token) {
  _pendingRequests.forEach(cb => cb(token))
  _pendingRequests = []
}

function _addPendingRequest(cb) {
  _pendingRequests.push(cb)
}

api.interceptors.request.use(config => {
  const method = config.method?.toUpperCase() || 'GET'
  const PUBLIC_ENDPOINTS = ['GET /accounts', 'POST /accounts']
  const isPublic = PUBLIC_ENDPOINTS.includes(`${method} ${config.url}`)

  const accountStore = useAccountStore()

  if (!isPublic) {
    let accountId = accountStore.currentAccountId
      || (accountStore.accounts.length > 0 && String(accountStore.accounts[0].id))
      || ''

    if (!accountId) {
      const authStore = useAuthStore()
      if (authStore.accountId) {
        accountId = String(authStore.accountId)
        accountStore.setCurrentAccount(accountId)
      }
    }

    if (!accountId) {
      console.warn('[API] 无有效账本ID，跳过请求:', config.url)
      return Promise.reject({ response: { data: { error: { code: 'NO_ACCOUNT', message: '请先创建账本', action: 'none' } } } })
    }

    config.headers['X-Account-ID'] = accountId
    if (config.method !== 'get' && config.method !== 'head') {
      config.headers['X-Operator'] = 'user'
    }
  }

  const token = localStorage.getItem('auth_access_token')
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  res => {
    if (res.status === 202 && res.data?._pending_confirm === undefined && res.data?.confirm_token) {
      console.log('[Confirm] AI危险操作需确认:', res.data.summary, 'token:', res.data.confirm_token)
      if (typeof window !== 'undefined' && window.__confirmDialogPoll) {
        window.__confirmDialogPoll()
      }
      return { _pending_confirm: true, ...res.data }
    }
    if (res.config.responseType === 'blob') {
      return res
    }
    return res.data
  },
  async err => {
    const originalRequest = err.config

    // 401 自动刷新 token（跳过认证相关请求自身）
    if (err.response?.status === 401
      && !originalRequest._retry
      && !originalRequest.url?.includes('/auth/login')
      && !originalRequest.url?.includes('/auth/refresh')
      && !originalRequest.url?.includes('/auth/logout')
      && !originalRequest.url?.includes('/auth/change-password')
    ) {
      if (_isRefreshing) {
        return new Promise(resolve => {
          _addPendingRequest(newToken => {
            originalRequest.headers['Authorization'] = `Bearer ${newToken}`
            resolve(api(originalRequest))
          })
        })
      }

      originalRequest._retry = true
      _isRefreshing = true

      const authStore = useAuthStore()
      const refreshToken = authStore.refreshToken

      if (!refreshToken) {
        _isRefreshing = false
        authStore.logout()
        window.location.href = '/login'
        return Promise.reject(err)
      }

      try {
        const data = await api.post('/auth/refresh', { refresh_token: refreshToken })
        const newToken = data.access_token
        authStore.accessToken = newToken
        authStore.expiresAt = Date.now() + (data.expires_in || 7200) * 1000
        authStore._persist()

        _onRefreshed(newToken)
        _isRefreshing = false

        originalRequest.headers['Authorization'] = `Bearer ${newToken}`
        return api(originalRequest)
      } catch {
        _isRefreshing = false
        _pendingRequests = []
        authStore.logout()
        window.location.href = '/login'
        return Promise.reject(err)
      }
    }

    const errData = err.response?.data
    if (errData?.error) {
      console.error(`[API Error] ${errData.error.code}: ${errData.error.message}`, errData.error)
      if (errData.error.code === 'ORDER_NOT_FOUND' && errData.error.message?.includes('账本不存在')) {
        localStorage.removeItem('currentAccountId')
        const store = useAccountStore()
        store.currentAccountId = ''
      }
    } else {
      console.error('API Error:', errData || err.message)
    }
    return Promise.reject(err)
  }
)

export default api
