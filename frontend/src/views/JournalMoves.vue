<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">凭证查询</span>
        </div>
      </template>

      <div class="filter-bar">
        <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" clearable />
        <el-select v-model="filterMoveType" placeholder="凭证类型" clearable style="width: 150px;">
          <el-option v-for="opt in moveTypeOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
        <el-button type="primary" @click="loadData(1)">查询</el-button>
      </div>

      <el-table :data="items" stripe v-loading="loading" @row-click="openDetail" style="cursor: pointer;">
        <template #empty><el-empty description="暂无数据" /></template>
        <el-table-column prop="id" label="凭证编号" width="100" />
        <el-table-column label="凭证类型" width="120">
          <template #default="{ row }">{{ moveTypeLabel(row.move_type) }}</template>
        </el-table-column>
        <el-table-column prop="description" label="摘要" min-width="200" show-overflow-tooltip />
        <el-table-column prop="move_date" label="日期" width="120" />
        <el-table-column label="借方合计" align="right" width="160">
          <template #default="{ row }">{{ formatMoney(row.total_debit) }}</template>
        </el-table-column>
        <el-table-column label="贷方合计" align="right" width="160">
          <template #default="{ row }">{{ formatMoney(row.total_credit) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="90" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click.stop="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-bar">
        <el-pagination v-model:current-page="page" v-model:page-size="pageSize" :total="total" :page-sizes="[10, 20, 50]" layout="total, sizes, prev, pager, next" @current-change="loadData" @size-change="loadData" />
      </div>
    </el-card>

    <el-drawer v-model="drawerVisible" :title="`凭证详情 #${detail?.id}`" size="600px">
      <template v-if="detail">
        <el-descriptions :column="2" border size="small" style="margin-bottom: 20px;">
          <el-descriptions-item label="凭证类型">{{ moveTypeLabel(detail.move_type) }}</el-descriptions-item>
          <el-descriptions-item label="日期">{{ detail.move_date }}</el-descriptions-item>
          <el-descriptions-item label="摘要" :span="2">{{ detail.description || '-' }}</el-descriptions-item>
        </el-descriptions>

        <el-table :data="detail.lines" stripe border size="small" :summary-method="detailSummary" show-summary>
          <el-table-column prop="account_code" label="科目编码" width="120" />
          <el-table-column prop="account_name" label="科目名称" min-width="160" />
          <el-table-column label="借方" align="right" width="140">
            <template #default="{ row }">{{ formatMoney(row.debit) }}</template>
          </el-table-column>
          <el-table-column label="贷方" align="right" width="140">
            <template #default="{ row }">{{ formatMoney(row.credit) }}</template>
          </el-table-column>
        </el-table>
      </template>
      <div v-else class="drawer-empty">
        <el-empty description="加载中..." />
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { getJournalMoves, getJournalMove } from '../api/finance'
import { formatMoney } from '../utils/format'
import { handleError } from '../api/index'
import { useAccountAwareData } from '../composables/useAccountAwareData'

const loading = ref(false)
const items = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

const dateRange = ref([])
const filterMoveType = ref('')

const drawerVisible = ref(false)
const detail = ref(null)

const moveTypeOptions = [
  { value: '', label: '全部' },
  { value: 'sale_order', label: '销售订单' },
  { value: 'purchase_order', label: '采购订单' },
  { value: 'receipt', label: '收款' },
  { value: 'payment', label: '付款' },
  { value: 'expense', label: '费用' },
]

const moveTypeLabel = (type) => {
  const map = { sale_order: '销售订单', purchase_order: '采购订单', receipt: '收款', payment: '付款', expense: '费用' }
  return map[type] || type
}

const loadData = async (p) => {
  if (p !== undefined) page.value = p
  loading.value = true
  try {
    const params = { skip: (page.value - 1) * pageSize.value, limit: pageSize.value }
    if (filterMoveType.value) params.move_type = filterMoveType.value
    if (dateRange.value && dateRange.value.length === 2) {
      params.date_from = dateRange.value[0]
      params.date_to = dateRange.value[1]
    }
    const res = await getJournalMoves(params)
    items.value = res.items || []
    total.value = res.total || 0
  } catch (e) {
    handleError(e, { defaultMsg: '加载凭证列表失败' })
  } finally {
    loading.value = false
  }
}

const openDetail = async (row) => {
  drawerVisible.value = true
  detail.value = null
  try {
    const res = await getJournalMove(row.id)
    detail.value = res
  } catch (e) {
    handleError(e, { defaultMsg: '加载凭证详情失败' })
    drawerVisible.value = false
  }
}

const detailSummary = ({ columns }) => {
  if (!detail.value) return columns.map(() => '')
  return columns.map((col, idx) => {
    if (idx === 0) return '合计'
    if (idx === 2) return formatMoney(detail.value.total_debit)
    if (idx === 3) return formatMoney(detail.value.total_credit)
    return ''
  })
}

useAccountAwareData(() => loadData(1))
</script>

<style scoped>
.drawer-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 200px;
}
</style>
