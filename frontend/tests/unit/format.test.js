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
})
