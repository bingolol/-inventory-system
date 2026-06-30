import axios from 'axios'
import { useAccountStore } from '../stores/account'
import { useAuthStore } from '../stores/auth'
import { handleError } from '../utils/errorHandler'

// 优先使用 Vite 环境变量，开发环境走 proxy，生产环境走绝对路径
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''
const baseURL = import.meta.env.VITE_API_BASE_URL
  ? `${import.meta.env.VITE_API_BASE_URL}/api`
  : '/api'

const api = axios.create({
  baseURL,
  timeout: 10000
})

// 导出baseURL供组件使用
export { API_BASE_URL, handleError }

// 统一处理image_url：相对路径→完整URL
export const resolveImageUrl = (url) => {
  if (!url) return ''
  if (url.startsWith('http')) return url
  return `${API_BASE_URL}${url}`
}

api.interceptors.request.use(config => {
  // 白名单：不需要账本ID的端点（获取列表/新建账本）
  const method = config.method?.toUpperCase() || 'GET'
  const PUBLIC_ENDPOINTS = ['GET /accounts', 'POST /accounts']
  const isPublic = PUBLIC_ENDPOINTS.includes(`${method} ${config.url}`)

  const accountStore = useAccountStore()

  if (!isPublic) {
    let accountId = accountStore.currentAccountId
      || (accountStore.accounts.length > 0 && String(accountStore.accounts[0].id))
      || ''

    // 尝试从登录时回传的默认账本初始化
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

  // 登录 token：如果存在，自动带 Authorization 头
  const token = localStorage.getItem('auth_token')
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  res => {
    // 202 是确认中间件返回的：AI 危险操作等待用户确认
    if (res.status === 202 && res.data?._pending_confirm === undefined && res.data?.confirm_token) {
      console.log('[Confirm] AI危险操作需确认:', res.data.summary, 'token:', res.data.confirm_token)
      // 通知确认对话框组件刷新
      if (typeof window !== 'undefined' && window.__confirmDialogPoll) {
        window.__confirmDialogPoll()
      }
      return { _pending_confirm: true, ...res.data }
    }
    // blob 请求返回完整响应对象，让调用方通过 res.data 获取 Blob
    if (res.config.responseType === 'blob') {
      return res
    }
    return res.data
  },
  err => {
    // 统一错误日志（结构化）
    const errData = err.response?.data
    if (errData?.error) {
      console.error(`[API Error] ${errData.error.code}: ${errData.error.message}`, errData.error)
      // 如果后端返回账本不存在，清除 localStorage 中的 stale ID
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