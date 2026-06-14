import { ElMessage } from 'element-plus'

/**
 * 统一错误处理器
 * 
 * @param {Error} error - Axios错误对象
 * @param {Object} options - 配置项
 * @param {string} [options.defaultMsg='操作失败'] - 默认错误消息
 * @param {boolean} [options.showDetail=true] - 是否显示详细错误
 */
export function handleError(error, options = {}) {
  const { defaultMsg = '操作失败', showDetail = true } = options
  
  let message = defaultMsg
  
  // 尝试从后端获取详细错误
  if (error.response?.data?.detail) {
    const detail = error.response.data.detail
    if (typeof detail === 'string') {
      message = showDetail ? detail : defaultMsg
    } else if (Array.isArray(detail)) {
      // Pydantic验证错误
      message = detail.map(d => `${d.loc?.join('.')}: ${d.msg}`).join('; ')
    }
  } else if (error.message) {
    message = error.message
  }
  
  ElMessage.error(message)
  console.error('[API Error]', error)
}
