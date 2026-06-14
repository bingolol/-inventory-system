import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'

/**
 * 订单表单 composable
 *
 * 封装采购/销售单的明细行管理、防重检查、合计计算等通用表单逻辑。
 * 从 Sales.vue / Purchases.vue 提取，通过配置区分订单类型。
 *
 * @param {Object} config
 * @param {string} config.orderType - 'sale' | 'purchase'
 * @param {Object} config.api - 订单API对象 { create, update, delete, getList }
 * @param {Function} config.onSuccess - 操作成功后的回调（如刷新列表）
 * @param {boolean} [config.autoFillPrice=false] - 选择商品时是否自动填充单价（采购=true，销售=false）
 */
export function useOrderForm(config) {
  const { orderType, api, onSuccess, autoFillPrice = false } = config

  // ── 操作反馈 ──
  const operationFeedback = ref({
    show: false,
    type: 'success', // 'success' | 'warning' | 'info'
    message: '',
    details: [] // [{ label: '库存变化', value: '-5' }, ...]
  })

  const clearFeedback = () => {
    operationFeedback.value.show = false
    operationFeedback.value.details = []
  }

  // ── 新建表单 ──
  const dialogVisible = ref(false)
  const form = ref({
    id: null,
    items: [{ product_id: null, quantity: 1, unit_price: 0 }]
  })
  const products = ref([])

  const orderTotal = computed(() =>
    form.value.items.reduce((sum, item) => sum + (item.quantity * item.unit_price), 0)
  )

  // ── 编辑表单 ──
  const editDialogVisible = ref(false)
  const editingId = ref(null)
  const editForm = ref({
    id: null,
    items: []
  })

  const editOrderTotal = computed(() =>
    editForm.value.items.reduce((sum, item) => sum + (item.quantity * item.unit_price), 0)
  )

  // ── 明细行操作（新建表单） ──
  const addItem = () => {
    form.value.items.push({ product_id: null, quantity: 1, unit_price: 0 })
  }

  const removeItem = (idx) => {
    form.value.items.splice(idx, 1)
  }

  const onItemProductChange = (idx) => {
    const currentProductId = form.value.items[idx].product_id
    if (!currentProductId) return

    // 自动填充单价（采购单取采购价）
    if (autoFillPrice) {
      const p = products.value.find(x => x.id === currentProductId)
      if (p) form.value.items[idx].unit_price = p.purchase_price
    }

    // 防重检查
    const dupIdx = form.value.items.findIndex((item, i) => i !== idx && item.product_id === currentProductId)
    if (dupIdx !== -1) {
      const prodName = products.value.find(p => p.id === currentProductId)?.name || `ID=${currentProductId}`
      ElMessage.warning(`商品"${prodName}"已在第${dupIdx + 1}行，请直接修改数量`)
      form.value.items[idx].product_id = null
    }
  }

  // ── 明细行操作（编辑表单） ──
  const addEditItem = () => {
    editForm.value.items.push({ product_id: null, quantity: 1, unit_price: 0 })
  }

  const removeEditItem = (idx) => {
    editForm.value.items.splice(idx, 1)
  }

  const onEditItemProductChange = (idx) => {
    const currentProductId = editForm.value.items[idx].product_id
    if (!currentProductId) return

    // 自动填充单价
    if (autoFillPrice) {
      const p = products.value.find(x => x.id === currentProductId)
      if (p) editForm.value.items[idx].unit_price = p.purchase_price
    }

    // 防重检查
    const dupIdx = editForm.value.items.findIndex((item, i) => i !== idx && item.product_id === currentProductId)
    if (dupIdx !== -1) {
      const prodName = products.value.find(p => p.id === currentProductId)?.name || `ID=${currentProductId}`
      ElMessage.warning(`商品"${prodName}"已在第${dupIdx + 1}行，请直接修改数量`)
      editForm.value.items[idx].product_id = null
    }
  }

  // ── 状态变更 ──
  const changeStatus = async (id, status) => {
    try {
      await api.update(id, { status })
      ElMessage.success('状态已更新')
      onSuccess?.()
    } catch (e) {
      ElMessage.error('更新失败')
    }
  }

  // ── 删除 ──
  const handleDelete = async (id) => {
    try {
      await api.delete(id)
      ElMessage.success('已删除')
      onSuccess?.()
    } catch (e) {
      ElMessage.error('删除失败')
    }
  }

  // ── 重置新建表单 ──
  const resetForm = (defaults = {}) => {
    form.value = {
      id: null,
      items: [{ product_id: null, quantity: 1, unit_price: 0 }],
      ...defaults
    }
  }

  // ── 设置编辑表单 ──
  const setEditForm = (row, defaults = {}) => {
    editingId.value = row.id
    editForm.value = {
      id: row.id,
      items: (row.items || []).map(item => ({
        product_id: item.product_id,
        quantity: Number(item.quantity),
        unit_price: Number(item.unit_price)
      })),
      ...defaults
    }
  }

  return {
    // 操作反馈
    operationFeedback,
    clearFeedback,
    // 新建表单
    dialogVisible,
    form,
    products,
    orderTotal,
    addItem,
    removeItem,
    onItemProductChange,
    resetForm,
    // 编辑表单
    editDialogVisible,
    editingId,
    editForm,
    editOrderTotal,
    addEditItem,
    removeEditItem,
    onEditItemProductChange,
    setEditForm,
    // 通用操作
    changeStatus,
    handleDelete
  }
}