const axios = require('axios')

// 完全模拟 api/index.js 的配置
const api = axios.create({
  baseURL: 'http://localhost:5175/api',
  timeout: 10000
})

// 模拟请求拦截器
api.interceptors.request.use(config => {
  let accountId = '1'  // 假设 localStorage 中有 currentAccountId = '1'
  config.headers['X-Account-ID'] = accountId
  console.log('→ 请求:', config.url, 'X-Account-ID:', accountId)
  return config
})

// 模拟响应拦截器
api.interceptors.response.use(
  res => {
    console.log('← 响应:', res.status, res.statusText)
    if (res.config.responseType === 'blob') {
      console.log('  这是 blob 响应，返回完整 response')
      return res
    }
    return res.data
  },
  err => {
    console.error('← 错误:', err.response?.status, err.response?.data || err.message)
    return Promise.reject(err)
  }
)

async function test() {
  console.log('=== 测试 exportProductsBatch ===')
  try {
    const res = await api.get('/export/products-batch', {
      params: { product_ids: '1,2,3', format: 'csv' },
      responseType: 'blob'
    })
    console.log('res.data 类型:', typeof res.data, '是Blob?', res.data instanceof Blob)
    console.log('res.data.constructor:', res.data?.constructor?.name)

    // 在 Node.js 中，axios 返回的 blob 实际上是 Buffer
    const buf = res.data
    console.log('Buffer 长度:', buf.length)
    console.log('内容前200字符:', buf.toString('utf8').substring(0, 200))
    console.log('✅ 成功!')
  } catch (e) {
    console.error('❌ 失败:', e.message)
  }
}

test()