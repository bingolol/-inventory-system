function toNumber(v) {
  if (v === null || v === undefined || v === '') return 0
  const n = Number(v)
  return Number.isNaN(n) ? 0 : n
}

export function calculateInvoiceAmounts(amountWithTax, amountWithoutTax, taxRate, mode) {
  const a = toNumber(amountWithTax)
  const b = toNumber(amountWithoutTax)
  const r = toNumber(taxRate)

  if (mode === '价税合计' && a > 0) {
    const withoutTax = a / (1 + r)
    const tax = a - withoutTax
    return {
      amount_without_tax: parseFloat(withoutTax.toFixed(2)),
      tax_amount: parseFloat(tax.toFixed(2)),
      amount_with_tax: a,
    }
  }

  if (mode === '不含税金额' && b > 0) {
    const tax = b * r
    const withTax = b + tax
    return {
      amount_without_tax: b,
      tax_amount: parseFloat(tax.toFixed(2)),
      amount_with_tax: parseFloat(withTax.toFixed(2)),
    }
  }

  return { amount_without_tax: 0, tax_amount: 0, amount_with_tax: 0 }
}
