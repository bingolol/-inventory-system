<template>
  <div>
    <el-table :data="invoices" stripe v-loading="loading" style="width: 100%">
      <template #empty>
        <el-empty description="暂无发票记录" />
      </template>
      <el-table-column prop="invoice_no" label="发票号码" min-width="150" />
      <el-table-column prop="direction" label="方向" min-width="80" align="center">
        <template #default="{ row }">
          <span class="status-badge" :class="row.direction === 'out' ? 'primary' : 'success'">
            {{ enumsStore.getLabel('invoice_direction', row.direction) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="invoice_type" label="类型" min-width="80" align="center">
        <template #default="{ row }">
          <span class="status-badge" :class="row.invoice_type === 'special' ? 'warning' : 'info'">
            {{ enumsStore.getLabel('invoice_type', row.invoice_type) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="tax_rate" label="税率" min-width="80" align="center">
        <template #default="{ row }">
          {{ Number(row.tax_rate * 100).toFixed(0) }}%
        </template>
      </el-table-column>
      <el-table-column prop="amount_without_tax" label="不含税金额" min-width="120" align="right">
        <template #default="{ row }">{{ formatMoney(row.amount_without_tax) }}</template>
      </el-table-column>
      <el-table-column prop="tax_amount" label="税额" min-width="100" align="right">
        <template #default="{ row }">{{ formatMoney(row.tax_amount) }}</template>
      </el-table-column>
      <el-table-column prop="amount_with_tax" label="价税合计" min-width="120" align="right">
        <template #default="{ row }">{{ formatMoney(row.amount_with_tax) }}</template>
      </el-table-column>
      <el-table-column prop="counterparty_name" label="对方名称" min-width="150" />
      <el-table-column label="开票日期" min-width="120">
        <template #default="{ row }">{{ formatDate(row.issue_date) }}</template>
      </el-table-column>
      <el-table-column prop="certification_status" label="认证状态" min-width="100" align="center">
        <template #default="{ row }">
          <span class="status-badge" :class="certificationClass(row.certification_status)">
            {{ certificationText(row.certification_status) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="260" align="center" fixed="right">
        <template #default="{ row }">
          <ActionColumn :actions="buildActions(row)" @click="(key) => handleAction(key, row)" />
        </template>
      </el-table-column>
    </el-table>

    <div v-if="showTotal" class="inv-total">
      <span>筛选合计：</span>
      <span class="inv-total-item">不含税 ¥{{ formatMoney(totalAmountWithoutTax) }}</span>
      <span class="inv-total-item">税额 ¥{{ formatMoney(totalTaxAmount) }}</span>
      <span class="inv-total-highlight">价税合计 ¥{{ formatMoney(totalAmountWithTax) }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { formatMoney, formatDate } from '../../utils/format'
import { useEnumsStore } from '../../stores/enums'
import ActionColumn from '../ActionColumn.vue'

const props = defineProps({
  invoices: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  showTotal: { type: Boolean, default: true }
})

const emit = defineEmits([
  'preview-pdf',
  'preview-image',
  'edit',
  'reverse',
  'certify',
  'uncertify'
])

const enumsStore = useEnumsStore()

const totalAmountWithoutTax = computed(() =>
  props.invoices.reduce((sum, item) => sum + (Number(item.amount_without_tax) || 0), 0)
)

const totalTaxAmount = computed(() =>
  props.invoices.reduce((sum, item) => sum + (Number(item.tax_amount) || 0), 0)
)

const totalAmountWithTax = computed(() =>
  props.invoices.reduce((sum, item) => sum + (Number(item.amount_with_tax) || 0), 0)
)

function certificationClass(status) {
  switch (status) {
    case 'pending': return 'warning'
    case 'certified': return 'success'
    case 'n_a': return 'info'
    default: return 'default'
  }
}

function certificationText(status) {
  switch (status) {
    case 'pending': return '未认证'
    case 'certified': return '已认证'
    case 'n_a': return '无需认证'
    default: return status
  }
}

function buildActions(row) {
  return [
    { key: 'preview', label: '预览', type: 'info', show: !!row.pdf_path },
    { key: 'image', label: '图片', type: 'info', show: !!row.image_url },
    { key: 'edit', label: '编辑', type: 'primary' },
    {
      key: 'reverse',
      label: '红冲',
      type: 'warning',
      confirm: '确定红冲此发票？（关联订单将自动取消）',
      show: !row.is_reversed
    },
    {
      key: 'certify',
      label: '认证',
      type: 'success',
      show: row.direction === 'in' && row.invoice_type === 'special' && row.certification_status !== 'certified'
    },
    {
      key: 'uncertify',
      label: '取消认证',
      type: 'warning',
      show: row.direction === 'in' && row.invoice_type === 'special' && row.certification_status === 'certified'
    }
  ]
}

function handleAction(key, row) {
  switch (key) {
    case 'preview':
      emit('preview-pdf', row.id)
      break
    case 'image':
      emit('preview-image', row)
      break
    case 'edit':
      emit('edit', row)
      break
    case 'reverse':
      emit('reverse', row)
      break
    case 'certify':
      emit('certify', row.id)
      break
    case 'uncertify':
      emit('uncertify', row)
      break
  }
}
</script>

<style scoped>
.inv-total {
  margin-top: 12px;
  padding: 10px 16px;
  background: var(--bg-elevated);
  border-radius: 8px;
  display: flex;
  align-items: center;
  gap: 24px;
  font-size: 14px;
  color: var(--text-secondary);
}
.inv-total-item {
  font-weight: 600;
  color: var(--text-regular);
}
.inv-total-highlight {
  font-weight: 700;
  color: var(--primary);
}
</style>
