import { describe, it, expect } from 'vitest'

// 提取 parseError 逻辑进行单元测试（不依赖 Element Plus）
function parseError(error) {
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

  if (error.response?.data?.detail) {
    const detail = error.response.data.detail
    const message = typeof detail === 'string'
      ? detail
      : Array.isArray(detail)
        ? detail.map(d => `${d.loc?.join('.')}: ${d.msg}`).join('; ')
        : String(detail)
    return { code: 'UNKNOWN', message, action: 'none', action_data: {}, data: {}, ai_instruction: '', status: error.response.status }
  }

  if (!error.response) {
    return { code: 'NETWORK_ERROR', message: '网络连接失败，请检查网络', action: 'retry', action_data: {}, data: {}, ai_instruction: 'STOP_RETRYING. 网络连接失败，请检查网络后重试。', status: 0 }
  }

  return { code: 'UNKNOWN', message: error.message || '未知错误', action: 'none', action_data: {}, data: {}, ai_instruction: '', status: error.response?.status }
}

describe('parseError', () => {
  it('parses new error format', () => {
    const error = {
      response: {
        status: 422,
        data: {
          error: {
            code: 'VALIDATION_ERROR',
            message: '名称不能为空',
            action: 'user_input',
            action_data: {},
            data: { field: 'name' },
            ai_instruction: 'STOP_RETRYING'
          }
        }
      }
    }
    const result = parseError(error)
    expect(result.code).toBe('VALIDATION_ERROR')
    expect(result.message).toBe('名称不能为空')
    expect(result.action).toBe('user_input')
    expect(result.status).toBe(422)
  })

  it('parses old detail format (string)', () => {
    const error = {
      response: {
        status: 400,
        data: { detail: '参数错误' }
      }
    }
    const result = parseError(error)
    expect(result.message).toBe('参数错误')
    expect(result.action).toBe('none')
  })

  it('parses old detail format (array)', () => {
    const error = {
      response: {
        status: 422,
        data: {
          detail: [
            { loc: ['body', 'name'], msg: '字段必填' },
            { loc: ['body', 'price'], msg: '必须大于0' }
          ]
        }
      }
    }
    const result = parseError(error)
    expect(result.message).toContain('body.name')
    expect(result.message).toContain('字段必填')
  })

  it('handles network error', () => {
    const error = { response: undefined, message: 'Network Error' }
    const result = parseError(error)
    expect(result.code).toBe('NETWORK_ERROR')
    expect(result.action).toBe('retry')
    expect(result.status).toBe(0)
  })

  it('handles unknown error', () => {
    const error = { response: { status: 500, data: {} } }
    const result = parseError(error)
    expect(result.code).toBe('UNKNOWN')
  })
})
