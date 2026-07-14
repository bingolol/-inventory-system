import { defineStore } from 'pinia'
import { ElMessage } from 'element-plus'
import commonApi from '../api/common'
import { useAccountStore } from './account'

export const useEnumsStore = defineStore('enums', {
  state: () => ({
    enums: null,  // { values: {...}, labels: {...} }
    loaded: false,
    error: false,
    loadedAccountId: ''  // 记录当前枚举对应的账本ID
  }),

  getters: {
    // 获取某枚举类型的所有值（数组）
    getValues: (state) => (type) => {
      if (!state.enums) return []
      return state.enums.values[type] || []
    },

    // 获取某枚举类型某值的中文标签
    getLabel: (state) => (type, value) => {
      if (!state.enums) return value
      return state.enums.labels[type]?.[value] || value
    },

    // ── 选项数组（{label, value} 格式，供 el-select 使用）──

    // 订单状态选项
    orderStatusOptions(state) {
      if (!state.enums) return []
      const values = state.enums.values.order_status || []
      const labels = state.enums.labels.order_status || {}
      return values.map(v => ({ label: labels[v] || v, value: v }))
    },

    // 支付状态选项
    paymentStatusOptions(state) {
      if (!state.enums) return []
      const values = state.enums.values.payment_status || []
      const labels = state.enums.labels.payment_status || {}
      return values.map(v => ({ label: labels[v] || v, value: v }))
    },

    // 支付方式选项
    paymentMethodOptions(state) {
      if (!state.enums) return []
      const values = state.enums.values.payment_method || []
      const labels = state.enums.labels.payment_method || {}
      return values.map(v => ({ label: labels[v] || v, value: v }))
    },

    // 发票方向选项
    invoiceDirectionOptions(state) {
      if (!state.enums) return []
      const values = state.enums.values.invoice_direction || []
      const labels = state.enums.labels.invoice_direction || {}
      return values.map(v => ({ label: labels[v] || v, value: v }))
    },

    // 发票类型选项
    invoiceTypeOptions(state) {
      if (!state.enums) return []
      const values = state.enums.values.invoice_type || []
      const labels = state.enums.labels.invoice_type || {}
      return values.map(v => ({ label: labels[v] || v, value: v }))
    },

    // 认证状态选项
    certificationStatusOptions(state) {
      if (!state.enums) return []
      const values = state.enums.values.certification_status || []
      const labels = state.enums.labels.certification_status || {}
      return values.map(v => ({ label: labels[v] || v, value: v }))
    },

    // 发票状态选项
    invoiceStatusOptions(state) {
      if (!state.enums) return []
      const values = state.enums.values.invoice_status || []
      const labels = state.enums.labels.invoice_status || {}
      return values.map(v => ({ label: labels[v] || v, value: v }))
    },

    // 费用类别选项（中文列表，label=value）
    expenseCategoryOptions(state) {
      if (!state.enums) return []
      const values = state.enums.values.expense_categories || []
      return values.map(v => ({ label: v, value: v }))
    },

    // 成本类型选项
    costTypeOptions(state) {
      if (!state.enums) return []
      const values = state.enums.values.cost_types || []
      return values.map(v => ({ label: v, value: v }))
    },

    // 个人支出类别选项
    personalExpenseCategoryOptions(state) {
      if (!state.enums) return []
      const values = state.enums.values.personal_expense_categories || []
      return values.map(v => ({ label: v, value: v }))
    },

    // 个人收入类别选项
    personalIncomeCategoryOptions(state) {
      if (!state.enums) return []
      const values = state.enums.values.personal_income_categories || []
      return values.map(v => ({ label: v, value: v }))
    },

    // 现金流类别选项
    flowCategoryOptions(state) {
      if (!state.enums) return []
      const values = state.enums.values.flow_category || []
      const labels = state.enums.labels.flow_category || {}
      return values.map(v => ({ label: labels[v] || v, value: v }))
    }
  },

  actions: {
    async fetchEnums(force = false) {
      const accountStore = useAccountStore()
      const currentId = accountStore.currentAccountId
      if (!force && this.loaded && this.loadedAccountId === currentId) return
      try {
        const data = await commonApi.getEnums()
        // 防止竞态：请求返回时账本已切换，则忽略此响应
        if (accountStore.currentAccountId !== currentId) return
        this.enums = data
        this.loaded = true
        this.loadedAccountId = currentId
      } catch (e) {
        this.error = true
        ElMessage.warning('系统选项加载失败，请刷新页面重试')
      }
    },

    // 强制刷新（用于账本切换后调用）
    async refreshEnums() {
      await this.fetchEnums(true)
    }
  }
})