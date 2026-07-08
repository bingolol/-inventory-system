<template>
  <span class="status-badge" :class="badgeClass">
    {{ tagLabel }}
  </span>
</template>

<script setup>
import { computed } from 'vue'
import { useEnumsStore } from '../stores/enums'

const props = defineProps({
  status: { type: String, default: '' },
  type: { type: String, default: 'project' },
  size: { type: String, default: 'default' },
  color: { type: String, default: null },   // 直接覆盖颜色
  label: { type: String, default: null }    // 直接覆盖文本
})

const enumsStore = useEnumsStore()

// ── 颜色映射 ──
const colorMap = {
  project: { ongoing: 'primary', completed: 'success', cancelled: 'info' },
  payment: { pending: 'warning', partial: 'warning', completed: 'success' },
  source: { sale_order: 'success', manual: 'info' },
  order: { pending: 'warning', completed: 'success', cancelled: 'danger' },
  payment_status: { unpaid: 'warning', paid: 'success' },
  invoice: { '已开': 'success', '未开': 'warning', '不需开': 'info' },
  receipt_method: { company: 'primary', private_advance: 'warning' },
  payment_method: { company: 'primary', private_advance: 'warning', cash: 'info' },
  functional_category: { '管理费用': 'primary', '销售费用': 'success', '财务费用': 'warning', '税金及附加': 'danger' }
}

const normalizedStatus = computed(() => props.status ?? '')

const badgeClass = computed(() => {
  if (props.color) return props.color
  if (!normalizedStatus.value) return 'info'
  const map = colorMap[props.type] || colorMap.project
  return map[normalizedStatus.value] || 'info'
})

// ── 标签文本 ──
const labelMap = {
  payment: { pending: '待收款', partial: '部分收取', completed: '已收' },
  source: { sale_order: '销售单自动', manual: '手动录入' },
  receipt_method: { company: '公司账户', private_advance: '个人垫付' },
  payment_method: { company: '公司账户', private_advance: '个人垫付', cash: '现金' }
}

const enumTypes = ['project', 'order', 'payment_status', 'certification_status', 'invoice_status', 'flow_category']

const tagLabel = computed(() => {
  if (props.label) return props.label
  if (!normalizedStatus.value) return '-'
  if (enumTypes.includes(props.type)) {
    return enumsStore.getLabel(props.type, normalizedStatus.value)
  }
  const map = labelMap[props.type]
  return map?.[normalizedStatus.value] || normalizedStatus.value
})
</script>
