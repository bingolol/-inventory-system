import axios from 'axios'
import { useAccountStore } from '../stores/account'
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
  const accountStore = useAccountStore()
  // 优先读 store（响应式、与 UI 同步），空值时从 accounts 列表取第一个，而非硬编码 '1'
  const accountId = accountStore.currentAccountId
    || (accountStore.accounts.length > 0 && String(accountStore.accounts[0].id))
    || ''
  if (accountId) {
    config.headers['X-Account-ID'] = accountId
  }
  // 不主动设置 X-Operator：后端默认 'user'，AI 客户端/外部 API 调用方需显式传 'X-Operator: ai' 才会被标记
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
    } else {
      console.error('API Error:', errData || err.message)
    }
    return Promise.reject(err)
  }
)

export default api