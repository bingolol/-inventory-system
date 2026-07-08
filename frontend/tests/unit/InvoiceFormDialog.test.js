import { describe, it, expect, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import InvoiceFormDialog from '../../src/components/invoices/InvoiceFormDialog.vue'

beforeEach(() => {
  setActivePinia(createPinia())
})

function createWrapper(props = {}) {
  return mount(InvoiceFormDialog, {
    props: {
      modelValue: true,
      invoice: null,
      ...props
    },
    global: {
      stubs: {
        'el-dialog': {
          template: '<div><slot /><slot name="footer" /></div>',
          props: ['modelValue']
        },
        'el-form': true,
        'el-form-item': true,
        'el-input': { template: '<input />' },
        'el-select': { template: '<select><slot /></select>' },
        'el-option': true,
        'el-radio-group': true,
        'el-radio': true,
        'el-date-picker': true,
        'el-upload': true,
        'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' },
        'el-icon': true,
        ImageUpload: true
      }
    }
  })
}

describe('InvoiceFormDialog', () => {
  it('新增模式标题为“新增发票”', () => {
    const wrapper = createWrapper()
    expect(wrapper.vm.isEdit).toBe(false)
  })

  it('编辑模式识别 invoice 存在', () => {
    const wrapper = createWrapper({ invoice: { id: 1, invoice_no: 'A' } })
    expect(wrapper.vm.isEdit).toBe(true)
  })

  it('编辑时把字符串税率转为 Number', () => {
    const wrapper = createWrapper({
      invoice: {
        id: 1,
        invoice_no: 'A',
        direction: 'out',
        invoice_type: 'ordinary',
        tax_rate: '0.13',
        amount_without_tax: '100',
        tax_amount: '13',
        amount_with_tax: '113',
        counterparty_name: 'B',
        issue_date: '2026-07-01',
        certification_status: 'n_a'
      }
    })
    expect(wrapper.vm.invoiceForm.tax_rate).toBe(0.13)
    expect(wrapper.vm.invoiceForm.amount_without_tax).toBe(100)
  })

  it('关闭时触发 update:modelValue(false)', async () => {
    const wrapper = createWrapper()
    wrapper.vm.close()
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('update:modelValue')).toBeTruthy()
    expect(wrapper.emitted('update:modelValue')[0]).toEqual([false])
  })

  it('保存时构建 payload 并触发 submit', async () => {
    const wrapper = createWrapper()
    wrapper.vm.invoiceForm.amount_with_tax = 113
    wrapper.vm.invoiceForm.tax_rate = 0.13
    wrapper.vm.save()
    await wrapper.vm.$nextTick()

    expect(wrapper.emitted('submit')).toBeTruthy()
    const payload = wrapper.emitted('submit')[0][0].payload
    expect(payload.amount_with_tax).toBe(113)
    expect(payload.tax_rate).toBe(0.13)
  })
})
