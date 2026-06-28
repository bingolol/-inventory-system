import { describe, it, expect } from 'vitest'
import { formatMoney, formatDateTime, formatDate, splitOrderNo } from '../../src/utils/format.js'

describe('formatMoney', () => {
  it('formats normal numbers with commas and 2 decimals', () => {
    expect(formatMoney(1234.5)).toBe('1,234.50')
    expect(formatMoney(1234567.89)).toBe('1,234,567.89')
  })

  it('handles zero', () => {
    expect(formatMoney(0)).toBe('0.00')
  })

  it('handles negative numbers', () => {
    expect(formatMoney(-1234.56)).toBe('-1,234.56')
  })

  it('handles string numbers', () => {
    expect(formatMoney('1234.56')).toBe('1,234.56')
  })

  it('returns 0.00 for null/undefined/empty', () => {
    expect(formatMoney(null)).toBe('0.00')
    expect(formatMoney(undefined)).toBe('0.00')
    expect(formatMoney('')).toBe('0.00')
  })

  it('returns 0.00 for non-numeric strings', () => {
    expect(formatMoney('abc')).toBe('0.00')
  })

  it('handles very large numbers', () => {
    expect(formatMoney(1234567890123)).toBe('1,234,567,890,123.00')
  })

  it('handles small numbers with rounding', () => {
    expect(formatMoney(0.005)).toBe('0.01')
    expect(formatMoney(0.004)).toBe('0.00')
  })

  it('handles boolean values', () => {
    expect(formatMoney(true)).toBe('1.00')
    expect(formatMoney(false)).toBe('0.00')
  })
})

describe('formatDateTime', () => {
  it('returns dash for null/undefined/empty', () => {
    expect(formatDateTime(null)).toBe('-')
    expect(formatDateTime(undefined)).toBe('-')
    expect(formatDateTime('')).toBe('-')
  })

  it('formats ISO datetime string', () => {
    const result = formatDateTime('2026-05-07T13:24:04')
    expect(result).toBe('2026-5-7-13:24')
  })

  it('formats with invalid date returns dash', () => {
    const result = formatDateTime('not-a-date')
    expect(result).toBe('-')
  })

  it('handles numeric timestamp', () => {
    expect(formatDateTime(1715069044000)).toBe('-')
  })
})

describe('formatDate', () => {
  it('returns dash for null/undefined/empty', () => {
    expect(formatDate(null)).toBe('-')
    expect(formatDate(undefined)).toBe('-')
    expect(formatDate('')).toBe('-')
  })

  it('formats ISO date string', () => {
    const result = formatDate('2026-05-07')
    expect(result).toBe('2026-5-7')
  })

  it('formats from ISO datetime', () => {
    const result = formatDate('2026-05-07T13:24:04')
    expect(result).toBe('2026-5-7')
  })
})

describe('splitOrderNo', () => {
  it('splits old format at first dash', () => {
    const result = splitOrderNo('SO20260507-100134-001')
    expect(result.line1).toBe('SO20260507')
    expect(result.line2).toBe('100134-001')
  })

  it('splits new format at third dash', () => {
    const result = splitOrderNo('CG2026—5-17-20:01-01')
    expect(result.line1).toBe('CG2026—5-17-20:01')
    expect(result.line2).toBe('01')
  })

  it('handles empty/null input', () => {
    const result = splitOrderNo('')
    expect(result.line1).toBe('-')
    expect(result.line2).toBe('')
  })

  it('handles order number without dash', () => {
    const result = splitOrderNo('SO20260507')
    expect(result.line1).toBe('SO20260507')
    expect(result.line2).toBe('')
  })

  it('handles null/undefined input', () => {
    const r1 = splitOrderNo(null)
    expect(r1.line1).toBe('-')
    expect(r1.line2).toBe('')
    const r2 = splitOrderNo(undefined)
    expect(r2.line1).toBe('-')
    expect(r2.line2).toBe('')
  })

  it('handles new format with fewer than 3 dashes', () => {
    const result = splitOrderNo('CG2026—5-17')
    expect(result.line1).toBe('CG2026—5-17')
    expect(result.line2).toBe('')
  })
})
