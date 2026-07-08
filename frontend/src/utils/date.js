/**
 * 日期工具函数
 *
 * 所有函数基于浏览器本地时间（中国时区 UTC+8）计算，
 * 避免 new Date().toISOString() 带来的 UTC 偏移问题。
 */

function pad(n) {
  return String(n).padStart(2, '0')
}

/**
 * 获取当前本地日期字符串 YYYY-MM-DD
 */
export function today() {
  const d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/**
 * 获取当前本地月份字符串 YYYY-MM
 */
export function currentMonth() {
  const d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}`
}

/**
 * 获取当前年份
 */
export function currentYear() {
  return new Date().getFullYear()
}

/**
 * 获取当前季度（1-4）
 */
export function currentQuarter() {
  return Math.ceil((new Date().getMonth() + 1) / 3)
}

/**
 * 获取当前本地日期时间字符串 YYYY-MM-DDTHH:mm:ss
 * 后端 datetime 字段按中国时区解析，因此使用本地时间而非 UTC。
 */
export function nowLocal() {
  const d = new Date()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}

/**
 * 获取指定年份的开始/结束日期
 */
export function yearStart(year = currentYear()) {
  return `${year}-01-01`
}

export function yearEnd(year = currentYear()) {
  return `${year}-12-31`
}

/**
 * 获取指定日期所在月的开始/结束日期
 * @param {Date|string} [date] - 默认今天
 */
export function monthStart(date = new Date()) {
  const d = date instanceof Date ? date : new Date(date)
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-01`
}

export function monthEnd(date = new Date()) {
  const d = date instanceof Date ? date : new Date(date)
  const lastDay = new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate()
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(lastDay)}`
}

/**
 * 获取月份范围（支持偏移）
 * @param {number} [offset=0] - 相对当前月的偏移，0 表示本月，-1 表示上月
 * @returns {{start: string, end: string, year: number, month: number}}
 */
export function getMonthRange(offset = 0) {
  const d = new Date()
  d.setMonth(d.getMonth() + offset)
  const y = d.getFullYear()
  const m = d.getMonth() + 1
  const lastDay = new Date(y, m, 0).getDate()
  return {
    start: `${y}-${pad(m)}-01`,
    end: `${y}-${pad(m)}-${pad(lastDay)}`,
    year: y,
    month: m
  }
}

/**
 * 判断日期字符串是否与指定月份相同（默认当前月）
 */
export function isSameMonth(dateStr, base = new Date()) {
  if (!dateStr) return false
  const d = new Date(dateStr)
  if (isNaN(d.getTime())) return false
  return d.getFullYear() === base.getFullYear() && d.getMonth() === base.getMonth()
}

/**
 * 生成年份列表
 * @param {number} [startOffset=-2] - 起始年偏移
 * @param {number} [endOffset=2] - 结束年偏移
 */
export function generateYears(startOffset = -2, endOffset = 2) {
  const current = currentYear()
  const years = []
  for (let i = current + startOffset; i <= current + endOffset; i++) {
    years.push(i)
  }
  return years
}

/**
 * 从 YYYY-MM 期间字符串计算开始/结束日期
 * @param {string} period - 如 "2026-07"
 * @returns {{start: string, end: string}}
 */
export function periodRange(period) {
  const [y, m] = String(period).split('-').map(Number)
  if (!y || !m) return { start: '', end: '' }
  const lastDay = new Date(y, m, 0).getDate()
  return {
    start: `${y}-${pad(m)}-01`,
    end: `${y}-${pad(m)}-${pad(lastDay)}`
  }
}
