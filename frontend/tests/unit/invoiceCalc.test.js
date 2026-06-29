import { describe, it, expect } from 'vitest'
import { calculateInvoiceAmounts } from '../../src/utils/invoiceCalc'

describe('calculateInvoiceAmounts', () => {
  describe('价税合计 mode', () => {
    it('正常计算价税合计 → 不含税金额和税额', () => {
      const r = calculateInvoiceAmounts(10100, 0, 0.01, '价税合计')
      expect(r.amount_without_tax).toBe(10000)
      expect(r.tax_amount).toBe(100)
      expect(r.amount_with_tax).toBe(10100)
    })

    it('handle NaN input → return zeros', () => {
      const r = calculateInvoiceAmounts(NaN, 0, 0.01, '价税合计')
      expect(r.amount_without_tax).toBe(0)
      expect(r.tax_amount).toBe(0)
      expect(r.amount_with_tax).toBe(0)
    })

    it('handle undefined input → return zeros', () => {
      const r = calculateInvoiceAmounts(undefined, 0, 0.01, '价税合计')
      expect(r.amount_without_tax).toBe(0)
      expect(r.tax_amount).toBe(0)
      expect(r.amount_with_tax).toBe(0)
    })

    it('handle null input → return zeros', () => {
      const r = calculateInvoiceAmounts(null, 0, 0.01, '价税合计')
      expect(r.amount_without_tax).toBe(0)
      expect(r.tax_amount).toBe(0)
      expect(r.amount_with_tax).toBe(0)
    })

    it('handle empty string → return zeros', () => {
      const r = calculateInvoiceAmounts('', 0, 0.01, '价税合计')
      expect(r.amount_without_tax).toBe(0)
      expect(r.tax_amount).toBe(0)
      expect(r.amount_with_tax).toBe(0)
    })

    it('handle NaN taxRate → treated as 0% tax', () => {
      const r = calculateInvoiceAmounts(10100, 0, NaN, '价税合计')
      expect(r.amount_without_tax).toBe(10100)
      expect(r.tax_amount).toBe(0)
      expect(r.amount_with_tax).toBe(10100)
    })
  })

  describe('不含税金额 mode', () => {
    it('正常计算不含税金额 → 税额和价税合计', () => {
      const r = calculateInvoiceAmounts(0, 10000, 0.01, '不含税金额')
      expect(r.amount_without_tax).toBe(10000)
      expect(r.tax_amount).toBe(100)
      expect(r.amount_with_tax).toBe(10100)
    })

    it('handle NaN input → return zeros', () => {
      const r = calculateInvoiceAmounts(0, NaN, 0.01, '不含税金额')
      expect(r.amount_without_tax).toBe(0)
      expect(r.tax_amount).toBe(0)
      expect(r.amount_with_tax).toBe(0)
    })
  })

  it('handle invalid mode → return zeros', () => {
    const r = calculateInvoiceAmounts(100, 0, 0.01, 'invalid')
    expect(r.amount_without_tax).toBe(0)
    expect(r.tax_amount).toBe(0)
    expect(r.amount_with_tax).toBe(0)
  })

  it('rounds to 2 decimal places', () => {
    const r = calculateInvoiceAmounts(101.1, 0, 0.03, '价税合计')
    expect(r.amount_without_tax).toBe(98.16)
    expect(r.tax_amount).toBe(2.94)
    expect(r.amount_with_tax).toBe(101.1)
  })
})
