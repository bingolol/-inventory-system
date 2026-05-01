const axios = require('axios')

async function testExport() {
  const api = axios.create({
    baseURL: 'http://localhost:5175/api',
    timeout: 10000
  })

  // 模拟拦截器中的逻辑
  api.interceptors.request.use(config => {
    let accountId = '1' // 默认值
    try {
      const stored = '1' // 模拟 localStorage
      if (stored) accountId = stored
    } catch (e) {
      console.warn('localStorage 不可用')
    }
    config.headers['X-Account-ID'] = accountId
    config.headers['X-Operator'] = 'user'
    console.log('→ 请求:', config.url)
    console.log('→ X-Account-ID:', config.headers['X-Account-ID'])
    return config
  })

  api.interceptors.response.use(
    res => {
      if (res.config.responseType === 'blob') {
        return res
      }
      return res.data
    },
    err => {
      console.error('← 错误:', err.response?.status, err.response?.data || err.message)
      return Promise.reject(err)
    }
  )

  try {
    console.log('=== 测试批量导出 ===')
    const res = await api.get('/export/products-batch', {
      params: { product_ids: '1,2,3', format: 'csv' },
      responseType: 'blob'
    })
    console.log('← 响应状态:', res.status)
    console.log('← 数据类型:', typeof res.data, res.data.constructor?.name)
    console.log('← 数据长度:', res.data.length || res.data.size)
    console.log('✅ 测试成功!')
  } catch (e) {
    console.error('❌ 测试失败:', e.message)
  }
}

testExport()