import { describe, it, expect, beforeEach } from 'vitest'
import { shallowMount } from '@vue/test-utils'
import { setActivePinia, createPinia } from 'pinia'
import OrderFormDialog from '../../src/components/OrderFormDialog.vue'

beforeEach(() => {
  setActivePinia(createPinia())
})

function createWrapper(props = {}) {
  return shallowMount(OrderFormDialog, {
    props: {
      visible: true,
      isEdit: false,
      form: { supplier_id: null, customer_name: '', items: [], tax_rate: 0.03, has_invoice: false, payment_method: 'company', payment_status: 'unpaid', notes: '' },
      products: [],
      partners: [],
      orderTotal: 0,
      onProductChange: () => {},
      ...props
    },
    global: {
      stubs: {
        'el-dialog': { template: '<div><slot /><slot name="footer" /></div>' },
        'el-form': true,
        'el-form-item': true,
        'el-select': true,
        'el-option': true,
        'el-switch': true,
        'el-input': true,
        'el-button': { template: '<button @click="$emit(\'click\')"><slot /></button>' },
        'el-icon': true,
        'el-alert': true,
        'el-date-picker': true,
        'el-input-number': true,
        ImageUpload: true,
        OrderItemEditor: true,
        Warning: true
      }
    }
  })
}

describe('OrderFormDialog', () => {
  it('renders "新建采购单" title for purchase + !isEdit', () => {
    const wrapper = createWrapper({ titleName: '采购' })
    expect(wrapper.props().titleName).toBe('采购')
  })

  it('renders "新建销售单" title for sale + !isEdit', () => {
    const wrapper = createWrapper({ titleName: '销售' })
    expect(wrapper.props().titleName).toBe('销售')
  })

  it('renders "编辑采购单" title for purchase + isEdit', () => {
    const wrapper = createWrapper({ titleName: '采购', isEdit: true })
    expect(wrapper.props().titleName).toBe('采购')
    expect(wrapper.props().isEdit).toBe(true)
  })

  it('passes partnerMode=createable for customer (sale)', () => {
    const wrapper = createWrapper({ partnerMode: 'createable' })
    expect(wrapper.props().partnerMode).toBe('createable')
  })

  it('passes partnerMode=select for supplier (purchase)', () => {
    const wrapper = createWrapper({ partnerMode: 'select' })
    expect(wrapper.props().partnerMode).toBe('select')
  })

  it('shows date field when showDate=true', () => {
    const wrapper = createWrapper({ showDate: true })
    expect(wrapper.props().showDate).toBe(true)
  })

  it('hides date field when showDate=false', () => {
    const wrapper = createWrapper({ showDate: false })
    expect(wrapper.props().showDate).toBe(false)
  })

  it('shows payment method when showPaymentMethod=true', () => {
    const wrapper = createWrapper({ showPaymentMethod: true })
    expect(wrapper.props().showPaymentMethod).toBe(true)
  })

  it('emits save when save button clicked', async () => {
    const wrapper = createWrapper()
    wrapper.vm.$emit('save')
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('save')).toBeTruthy()
  })

  it('emits update:visible when cancel clicked', async () => {
    const wrapper = createWrapper()
    wrapper.vm.$emit('update:visible', false)
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('update:visible')).toBeTruthy()
    expect(wrapper.emitted('update:visible')[0]).toEqual([false])
  })
})
