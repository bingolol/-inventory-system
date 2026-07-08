/**
 * 统一税率选项常量 — 所有税率下拉框共用
 *
 * 与后端 policy/vat_facts.py 的 VAT_LEGAL_RATES 保持一致：
 *   0%  — 零税率（出口/免税项目）
 *   1%  — 小规模纳税人减按征收率
 *   3%  — 小规模纳税人法定征收率
 *   6%  — 一般纳税人（现代服务业/金融服务等）
 *   9%  — 一般纳税人（农产品/不动产/运输等）
 *   13% — 一般纳税人基本税率
 */
export const TAX_RATE_OPTIONS = [
  { label: '0%', value: 0 },
  { label: '1%', value: 0.01 },
  { label: '3%', value: 0.03 },
  { label: '6%', value: 0.06 },
  { label: '9%', value: 0.09 },
  { label: '13%', value: 0.13 },
]
