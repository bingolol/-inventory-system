/**
 * 格式化金额（千分位 + 2位小数）
 * @param {number|string|null|undefined} value - 金额值
 * @returns {string} 如 "1,234.56"
 */
export const formatMoney = (value) => {
  if (value === null || value === undefined || value === '') return '0.00'
  const num = Number(value)
  if (isNaN(num)) return '0.00'
  return num.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

/**
 * 日期时间格式化工具
 *
 * 后端返回的 datetime 字符串无时区后缀（如 2026-05-07T13:24:04），
 * 统一按中国时区（UTC+8）解析显示，不依赖浏览器本地时区。
 */

function parseChinaDate(str) {
  if (!str) return null
  if (typeof str !== 'string') return null
  const [datePart, timePart] = str.split('T')
  if (!datePart) return null
  const [y, M, d] = datePart.split('-').map(Number)
  if (!y || !M || !d) return null
  if (timePart) {
    const [h, m] = timePart.split(':').map(Number)
    return { y, M, d, h: h || 0, m: m || 0 }
  }
  return { y, M, d }
}

/**
 * 格式化日期时间（含时分，无秒）
 * @param {string|null} str - ISO datetime 字符串
 * @returns {string} 如 "2026-6-28-11:08"
 */
export const formatDateTime = (str) => {
  const p = parseChinaDate(str)
  if (!p) return '-'
  const m = String(p.m).padStart(2, '0')
  return `${p.y}-${p.M}-${p.d}-${p.h}:${m}`
}

/**
 * 格式化日期（仅年月日）
 * @param {string|null} str - ISO datetime 或 date 字符串
 * @returns {string} 如 "2026-6-28"
 */
export const formatDate = (str) => {
  const p = parseChinaDate(str)
  if (!p) return '-'
  return `${p.y}-${p.M}-${p.d}`
}

/**
 * 将订单号分割为双行显示的两部分
 * 新格式如 CG2026—5-17-20:01-01 → 第一行 CG2026—5-17，第二行 20:01-01
 * 旧格式如 SO20260507-100134-001 → 第一行 SO20260507，第二行 100134-001
 * @param {string} orderNo - 订单号
 * @returns {{ line1: string, line2: string }}
 */
export const splitOrderNo = (orderNo) => {
  if (!orderNo) return { line1: '-', line2: '' }
  // 检测新格式：含中文破折号 —
  if (orderNo.includes('—')) {
    // CG2026—5-17-20:01-01，在第3个半角 - 处分割
    let dashCount = 0
    for (let i = 0; i < orderNo.length; i++) {
      if (orderNo[i] === '-') {
        dashCount++
        if (dashCount === 3) {
          return { line1: orderNo.slice(0, i), line2: orderNo.slice(i + 1) }
        }
      }
    }
    return { line1: orderNo, line2: '' }
  }
  // 旧格式：SO20260507-100134-001，在第1个 - 处分割
  const firstDash = orderNo.indexOf('-')
  if (firstDash === -1) return { line1: orderNo, line2: '' }
  return { line1: orderNo.slice(0, firstDash), line2: orderNo.slice(firstDash + 1) }
}