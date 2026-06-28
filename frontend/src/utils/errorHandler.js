import { ElMessage, ElMessageBox } from 'element-plus'

// Action 处理器：根据后端返回的 action 指令决定前端行为
// 后端错误码 → 用户可操作的排查提示
const ERROR_HINTS = {
  VALIDATION_ERROR: '请检查输入数据格式是否正确',
  NOT_FOUND: '请确认该记录是否存在',
  ORDER_NOT_FOUND: '请检查订单号是否正确',
  PRODUCT_NOT_FOUND: '请检查商品是否存在',
  BANK_ACCOUNT_NOT_FOUND: '请先创建银行账户',
  INVENTORY_SHORTAGE: '库存不足，请检查库存数量或调整采购计划',
  DUPLICATE_ENTRY: '该记录已存在，请检查是否重复录入',
  INTERNAL_ERROR: '系统内部错误，请稍后重试，如持续出现请联系管理员',
}

const ACTION_HANDLERS = {
  none: (errorInfo) => {
    const msg = errorInfo.message || '操作失败'
    console.warn(`[${errorInfo.code}]`, msg, errorInfo.data || '')
    ElMessage.error(msg)
  },

  retry: (errorInfo, callbacks) => {
    if (callbacks.onRetry) {
      ElMessageBox.confirm(
        `${errorInfo.message}，是否重试？`,
        '操作失败',
        { confirmButtonText: '重试', cancelButtonText: '取消', type: 'warning' }
      ).then(callbacks.onRetry).catch(() => {})
    } else {
      ElMessage.error(errorInfo.message)
    }
  },

  user_confirm: (errorInfo, callbacks) => {
    const { confirm_text, options } = errorInfo.action_data
    const confirmBtn = options?.[0] || '确认'
    const cancelBtn = options?.[1] || '取消'

    ElMessageBox.confirm(
      confirm_text || errorInfo.message,
      '请确认',
      { confirmButtonText: confirmBtn, cancelButtonText: cancelBtn, type: 'warning' }
    ).then(() => callbacks.onConfirm?.(errorInfo)).catch(() => {})
  },

  user_input: (errorInfo) => {
    ElMessage.error(errorInfo.message)
    // 尝试高亮表单字段
    const firstField = errorInfo.data?.field
    if (firstField) {
      setTimeout(() => {
        document.querySelector(`[prop="${firstField}"]`)?.scrollIntoView({ behavior: 'smooth' })
      }, 100)
    }
  },

  user_select: (errorInfo, callbacks) => {
    const { options } = errorInfo.action_data
    if (options?.length) {
      ElMessageBox.confirm(
        errorInfo.message,
        '请选择',
        { confirmButtonText: options[0], cancelButtonText: options[1] || '取消', type: 'info' }
      ).then(() => callbacks.onSelect?.(options[0])).catch(() => {})
    } else {
      ElMessage.error(errorInfo.message)
    }
  },

  login: () => {
    ElMessage.warning('登录已过期，请重新登录')
  },

  contact_admin: (errorInfo) => {
    const msg = errorInfo.message || '操作失败'
    console.error('[SYSTEM_ERROR]', errorInfo.code, msg, errorInfo.data)
    ElMessage.error(msg)
  },
}

/**
 * 解析后端错误响应，提取结构化信息
 */
function parseError(error) {
  // 新格式：{ error: { code, message, action, action_data, data, ai_instruction } }
  if (error.response?.data?.error) {
    const { code, message, action, action_data, data, ai_instruction } = error.response.data.error
    return {
      code: code || 'UNKNOWN',
      message: message || '操作失败',
      action: action || 'none',
      action_data: action_data || {},
      data: data || {},
      ai_instruction: ai_instruction || '',
      status: error.response.status,
    }
  }

  // 兼容旧格式：{ detail: "..." }
  if (error.response?.data?.detail) {
    const detail = error.response.data.detail
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map(d => `${d.loc?.join('.')}: ${d.msg}`).join('; ')
        : String(detail)
    return { code: 'UNKNOWN', message, action: 'none', action_data: {}, data: {}, ai_instruction: '', status: error.response.status }
  }

  // 网络错误
  if (!error.response) {
    return { code: 'NETWORK_ERROR', message: '网络连接失败，请检查网络', action: 'retry', action_data: {}, data: {}, ai_instruction: 'STOP_RETRYING. 网络连接失败，请检查网络后重试。', status: 0 }
  }

  // 其他
  return { code: 'UNKNOWN', message: error.message || '未知错误', action: 'none', action_data: {}, data: {}, ai_instruction: '', status: error.response?.status }
}

/**
 * 统一错误处理器（增强版）
 *
 * @param {Error} error - Axios 错误对象
 * @param {Object} options
 * @param {string} [options.defaultMsg='操作失败'] - 默认错误消息
 * @param {Function} [options.onRetry] - 重试回调
 * @param {Function} [options.onConfirm] - 确认回调
 * @param {Function} [options.onSelect] - 选择回调
 * @param {'auto'|'silent'|'message'} [options.feedback='auto'] - 反馈方式
 * @returns {Object} errorInfo - 结构化错误信息
 */
export function handleError(error, options = {}) {
  const {
    defaultMsg = '操作失败',
    onRetry = null,
    onConfirm = null,
    onSelect = null,
    feedback = 'auto',
  } = options

  const errorInfo = parseError(error)

  // 用 defaultMsg 兜底空消息
  if (!errorInfo.message || errorInfo.message === '未知错误') {
    errorInfo.message = defaultMsg
  }

  // 静默模式：只记日志不弹消息
  if (feedback === 'silent') {
    console.error('[API Error]', errorInfo)
    return errorInfo
  }

  // 根据 action 分发到对应处理器
  const handler = ACTION_HANDLERS[errorInfo.action] || ACTION_HANDLERS.none
  handler(errorInfo, { onRetry, onConfirm, onSelect })

  console.error('[API Error]', errorInfo)
  return errorInfo
}
