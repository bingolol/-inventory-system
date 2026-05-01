/**
 * 模拟浏览器环境下 axios 的完整请求流程
 * 包括：请求拦截器、响应拦截器、blob 处理
 */
import axios from 'axios'

// 模拟浏览器 localStorage
const mockLocalStorage = {
  _data: {},
  getItem(key) { return this._data[key] || null },
  setItem(key, value) { this._data[key] = String(value) },
  removeItem(key) { delete this._data[key] },
  clear() { this._data = {} }
}

// 模拟 window.URL
const mockURL = {
  _urls: new Map(),
  _counter: 0,
  createObjectURL(blob) {
    const id = `blob://mock-${++this._counter}`
    this._urls.set(id, blob)
    return id
  },
  revokeObjectURL(url) {
    this._urls.delete(url)
  }
}

// 模拟 document
const mockDocument = {
  createElement(tag) {
    return {
      tagName: tag,
      href: '',
      _attrs: new Map(),
      setAttribute(k, v) { this._attrs.set(k, v) },
      getAttribute(k) { return this._attrs.get(k) },
      click() { console.log('[模拟点击] 下载:', this.getAttribute('download'), 'href:', this.href) },
      remove() { console.log('[模拟移除] 元素已移除') }
    }
  },
  body: {
    _children: [],
    appendChild(el) { this._children.push(el); console.log('[模拟DOM] 添加元素') },
    removeChild(el) {
      const idx = this._children.indexOf(el)
      if (idx >= 0) this._children.splice(idx, 1)
      console.log('[模拟DOM] 移除元素')
    }
  }
}

// 模拟浏览器环境
global.localStorage = mockLocalStorage
global.window = { URL: mockURL }
global.document = mockDocument

// 模拟 api/index.js 的完整逻辑
const API_BASE_URL = ''
const baseURL = '/api'

const api = axios.create({
  baseURL: 'http://localhost:5176/api',
  timeout: 10000
})

// 请求拦截器（与 api/index.js 完全一致）
api.interceptors.request.use(config => {
  let accountId = '1' // 默认使用账本1（日运办公）
  try {
    const stored = localStorage.getItem('currentAccountId')
    if (stored) {
      accountId = stored
    } else {
      localStorage.setItem('currentAccountId', accountId)
    }
  } catch (e) {
    console.warn('[API] localStorage 不可用，使用默认 accountId:', accountId)
  }
  config.headers['X-Account-ID'] = accountId
  config.headers['X-Operator'] = 'user'
  console.log('[拦截器] 请求:', config.url)
  console.log('[拦截器] X-Account-ID:', accountId)
  return config
})

// 响应拦截器（与 api/index.js 完全一致）
api.interceptors.response.use(
  res => {
    console.log('[拦截器] 响应状态:', res.status)
    if (res.config.responseType === 'blob') {
      console.log('[拦截器] blob 响应，返回完整 response')
      console.log('[拦截器] res.data 类型:', typeof res.data, res.data?.constructor?.name || '')
      return res
    }
    return res.data
  },
  err => {
    console.error('[拦截器] 错误:', err.response?.status, err.response?.data || err.message)
    return Promise.reject(err)
  }
)

// 导出方法（与 api/index.js 完全一致）
const exportProductsBatch = async (productIds, format = 'excel') => {
  console.log('=== 调用 exportProductsBatch ===')
  const res = await api.get('/export/products-batch', {
    params: { product_ids: productIds.join(','), format },
    responseType: 'blob'
  })

  const blob = res.data
  console.log('[exportProductsBatch] blob 类型:', blob.constructor.name)
  console.log('[exportProductsBatch] blob size:', blob.size || blob.length)

  const ext = format === 'csv' ? 'csv' : 'xlsx'
  const mime = format === 'csv'
    ? 'text/csv'
    : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  const url = window.URL.createObjectURL(new Blob([blob], { type: mime }))
  const link = document.createElement('a')
  link.href = url
  link.setAttribute('download', `库存商品导出_${productIds.length}条.${ext}`)
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
  return true
}

// 模拟 Products.vue 的 exportBatch
const exportBatch = async (format) => {
  const selectedRows = [{ id: 1 }, { id: 2 }]
  if (selectedRows.length === 0) {
    console.log('请先选择要导出的商品')
    return
  }
  try {
    const ids = selectedRows.map(r => r.id)
    console.log('[exportBatch] 准备导出:', ids, format)
    await exportProductsBatch(ids, format)
    console.log('✅ 导出成功')
  } catch (e) {
    console.error('❌ 导出失败:', e.message)
    const detail = e.response?.data?.detail || e.message || '未知错误'
    console.error('详细错误:', detail)
  }
}

// 运行测试
async function test() {
  console.log('\n=== 测试场景1: localStorage 为空（首次使用）===')
  localStorage.clear()
  await exportBatch('csv')

  console.log('\n=== 测试场景2: localStorage 已有 accountId ===')
  localStorage.setItem('currentAccountId', '2')
  await exportBatch('excel')

  console.log('\n=== 测试场景3: localStorage 被禁用 ===')
  const origGetItem = localStorage.getItem
  const origSetItem = localStorage.setItem
  localStorage.getItem = () => { throw new Error('localStorage disabled') }
  localStorage.setItem = () => { throw new Error('localStorage disabled') }
  await exportBatch('csv')
  localStorage.getItem = origGetItem
  localStorage.setItem = origSetItem
}

test()