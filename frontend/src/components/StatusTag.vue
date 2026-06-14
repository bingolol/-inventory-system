<template>
  <el-tag :type="tagType" :size="size">
    {{ tagLabel }}
  </el-tag>
</template>

<script setup>
import { computed } from 'vue'
import { useEnumsStore } from '../stores/enums'

const props = defineProps({
  status: { type: String, required: true },
  type: { type: String, default: 'project' },   // project | payment | source | order | payment_status | invoice
  size: { type: String, default: 'default' }
})

const enumsStore = useEnumsStore()

// ── 颜色映射 ──
const colorMap = {
  project: { ongoing: 'primary', completed: 'success', cancelled: 'info' },
  payment: { pending: 'warning', partial: 'warning', completed: 'success' },
  source: { sale_order: 'success', manual: 'info' },
  order: { pending: 'warning', completed: 'success', cancelled: 'danger' },
  payment_status: { unpaid: 'warning', paid: 'success' },
  invoice: { '已开': 'success', '未开': 'warning', '不需开': 'info' }
}

const tagType = computed(() => {
  const map = colorMap[props.type] || colorMap.project
  return map[props.status] || 'info'
})

// ── 标签文本 ──
const labelMap = {
  payment: { pending: '待收款', partial: '部分收取', completed: '已收' },
  source: { sale_order: '销售单自动', manual: '手动录入' }
}

const tagLabel = computed(() => {
  if (props.type === 'project') {
    return enumsStore.getLabel('project_status', props.status)
  }
  if (props.type === 'order') {
    return enumsStore.getLabel('order_status', props.status)
  }
  if (props.type === 'payment_status') {
    return enumsStore.getLabel('payment_status', props.status)
  }
  const map = labelMap[props.type]
  return map?.[props.status] || props.status
})
</script>