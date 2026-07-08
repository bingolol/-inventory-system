import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import InvoiceTaxStats from '../../src/components/invoices/InvoiceTaxStats.vue'

describe('InvoiceTaxStats', () => {
  it('渲染三个统计卡片', () => {
    const wrapper = mount(InvoiceTaxStats, {
      props: { outputTax: 100, inputTax: 50, taxPayable: 50 }
    })
    expect(wrapper.text()).toContain('销项税额')
    expect(wrapper.text()).toContain('进项税额')
    expect(wrapper.text()).toContain('应纳税额')
  })

  it('金额使用 formatMoney 格式化', () => {
    const wrapper = mount(InvoiceTaxStats, {
      props: { outputTax: 1234.5, inputTax: 0, taxPayable: -100 }
    })
    expect(wrapper.text()).toContain('1,234.50')
  })

  it('缺省值为 0 时不报错', () => {
    const wrapper = mount(InvoiceTaxStats)
    expect(wrapper.text()).toContain('0.00')
  })
})
