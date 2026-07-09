/**
 * 前端业务/会计术语映射层
 *
 * 统一收敛散落在组件中的中文标签、API 字段名、表单字段名，
 * 避免销售/采购多处 hardcode 不一致（如 sale_date vs business_date）。
 */

export const ORDER_TYPES = {
  sale: {
    key: 'sale',
    title: '销售',
    orderLabel: '销售单',
    partnerLabel: '客户',
    partnerMode: 'createable',
    partnerField: 'customer_name',     // 表单中使用的字段名
    partnerPropName: 'customer_name',  // 列表中展示的属性名
    partnerApiField: 'customer_id',    // 提交 API 时使用的字段名
    dateLabel: '销售日期',
    dateFormField: 'business_date',    // 统一使用业务日期
    dateApiField: 'business_date',
    showPaymentMethod: false,
    showStock: true,
    showCustomPrice: true,
    autoFillPrice: false,
    paymentStatusLabel: '收款状态',
    confirmText: '确认销售',
    addLabel: '新建销售',
    emptyLabel: '销售记录',
    businessType: 'sale',
    exportType: 'sales',
    feedback: {
      createSuccess: '销售成功',
      inventoryLabel: '库存扣减',
      inventoryValue: '零售出库',
      itemCountLabel: '销售商品数',
      createError: '销售失败，请检查库存和客户信息是否正确',
      editError: '修改失败，请检查输入数据是否正确',
    },
  },
  purchase: {
    key: 'purchase',
    title: '采购',
    orderLabel: '采购单',
    partnerLabel: '供应商',
    partnerMode: 'select',
    partnerField: 'supplier_id',
    partnerPropName: 'supplier_name',
    partnerApiField: 'supplier_id',
    dateLabel: '采购日期',
    dateFormField: 'business_date',
    dateApiField: 'business_date',
    showPaymentMethod: true,
    showStock: false,
    showCustomPrice: false,
    autoFillPrice: true,
    paymentStatusLabel: '付款状态',
    confirmText: '确认采购',
    addLabel: '新建采购',
    emptyLabel: '采购记录',
    businessType: 'purchase',
    exportType: 'purchases',
    feedback: {
      createSuccess: '采购成功，已自动入库',
      inventoryLabel: '入库商品数',
      totalQtyLabel: '总数量',
      createError: '采购失败，请检查输入数据是否正确',
      editError: '修改失败，请检查输入数据是否正确',
    },
  },
}

/**
 * 获取订单类型配置
 * @param {string} orderType - 'sale' | 'purchase'
 * @returns {Object}
 */
export function getOrderTerminology(orderType) {
  return ORDER_TYPES[orderType] || ORDER_TYPES.purchase
}

/**
 * 通用字段标签
 */
export const FIELD_LABELS = {
  orderNo: '单号',
  productCount: '商品数',
  totalPrice: '总价',
  invoiced: '已开票',
  paymentMethod: '支付方式',
  paymentStatus: '支付状态',
  status: '状态',
  date: '日期',
  notes: '备注',
  attachment: '附件',
  operation: '操作',
  product: '商品',
  quantity: '数量',
  unitPrice: '单价',
  subtotal: '小计',
  yes: '是',
  no: '否',
  none: '无',
  search: '搜索单号/供应商/项目',
  dateRangeStart: '开始日期',
  dateRangeEnd: '结束日期',
  statusFilter: '状态筛选',
  export: '导出',
  cancel: '取消',
  save: '保存修改',
  confirm: '确认',
  delete: '删除',
}

/**
 * 构建销售/采购创建/更新的 API 请求体
 *
 * @param {Object} params
 * @param {string} params.orderType - 'sale' | 'purchase'
 * @param {Object} params.form - 表单数据
 * @param {Array} params.items - 商品明细
 * @param {number|null} params.partnerId - 客户/供应商 ID
 */
export function buildOrderPayload({ orderType, form, items, partnerId, includeDate = true }) {
  const t = getOrderTerminology(orderType)
  const base = {
    has_invoice: form.has_invoice,
    payment_status: form.payment_status,
    notes: form.notes,
    items,
  }

  if (orderType === 'sale') {
    return {
      ...base,
      customer_id: partnerId,
      total_price: form.total_price ?? undefined,
      ...(includeDate ? { business_date: form[t.dateFormField] } : {}),
    }
  }

  return {
    ...base,
    supplier_id: partnerId,
    tax_rate: form.tax_rate,
    payment_method: form.payment_method,
    ...(includeDate ? { business_date: form[t.dateFormField] } : {}),
  }
}
