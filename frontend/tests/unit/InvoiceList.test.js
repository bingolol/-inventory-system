import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import InvoiceList from '../../src/components/invoices/InvoiceList.vue'

beforeEach(() => {
  setActivePinia(createPinia())
})

function createWrapper(props = {}) {
  return mount(InvoiceList, {
    props: {
      invoices: [],
      loading: false,
      ...props
    },
    global: {
      plugins: [ElementPlus],
      stubs: {
        'el-table-column': true,
        'el-empty': true,
        ActionColumn: { template: '<div class="action-column"><slot /></div>' }
      }
    }
  })
}

describe('InvoiceList', () => {
  it('空数据时渲染空状态插槽', () => {
    const wrapper = createWrapper()
    expect(wrapper.find('el-empty-stub').exists()).toBe(true)
  })

  it('正确计算筛选合计', () => {
    const wrapper = createWrapper({
      invoices: [
        { amount_without_tax: 100, tax_amount: 13, amount_with_tax: 113 },
        { amount_without_tax: 200, tax_amount: 26, amount_with_tax: 226 }
      ]
    })
    expect(wrapper.vm.totalAmountWithoutTax).toBe(300)
    expect(wrapper.vm.totalTaxAmount).toBe(39)
    expect(wrapper.vm.totalAmountWithTax).toBe(339)
  })

  it('认证状态文本映射正确', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.certificationText('pending')).toBe('未认证')
    expect(wrapper.vm.certificationText('certified')).toBe('已认证')
    expect(wrapper.vm.certificationText('n_a')).toBe('无需认证')
  })

  it('操作按钮按行状态生成：未认证进项专票显示认证', () => {
    const wrapper = createWrapper()
    const actions = wrapper.vm.buildActions({
      pdf_path: '/x.pdf',
      image_url: '/x.jpg',
      direction: 'in',
      invoice_type: 'special',
      certification_status: 'pending',
      is_reversed: false
    })
    const visible = actions.filter(a => a.show !== false)
    const keys = visible.map(a => a.key)
    expect(keys).toContain('preview')
    expect(keys).toContain('image')
    expect(keys).toContain('edit')
    expect(keys).toContain('reverse')
    expect(keys).toContain('certify')
    expect(keys).not.toContain('uncertify')
  })

  it('已认证进项专票显示取消认证', () => {
    const wrapper = createWrapper()
    const actions = wrapper.vm.buildActions({
      direction: 'in',
      invoice_type: 'special',
      certification_status: 'certified',
      is_reversed: false
    })
    const visible = actions.filter(a => a.show !== false)
    const keys = visible.map(a => a.key)
    expect(keys).toContain('uncertify')
    expect(keys).not.toContain('certify')
  })
})
