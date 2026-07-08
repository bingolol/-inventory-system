<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">会计凭证</span>
          <span style="font-size:12px;color:var(--text-placeholder);">由业务单据自动生成</span>
        </div>
      </template>

      <div class="filter-bar">
        <el-date-picker v-model="filters.date_from" type="date" placeholder="开始日期" value-format="YYYY-MM-DD" @change="search" style="width:150px;" />
        <el-date-picker v-model="filters.date_to" type="date" placeholder="结束日期" value-format="YYYY-MM-DD" @change="search" style="width:150px;" />
        <el-select v-model="filters.move_type" placeholder="凭证类型" clearable style="width:140px;" @change="search">
          <el-option v-for="opt in typeOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
        <el-button type="primary" @click="search">查询</el-button>
      </div>

      <el-table :data="list" stripe v-loading="loading" @row-click="openDetail" class="jm-table">
        <template #empty><el-empty description="暂无凭证数据" /></template>
        <el-table-column prop="id" label="凭证号" min-width="90" />
        <el-table-column label="凭证类型" min-width="110">
          <template #default="{ row }">{{ typeLabel(row.move_type) }}</template>
        </el-table-column>
        <el-table-column prop="ref" label="摘要" min-width="200" show-overflow-tooltip />
        <el-table-column label="会计日期" min-width="100">
          <template #default="{ row }">{{ formatDate(row.date) }}</template>
        </el-table-column>
        <el-table-column label="创建时间" min-width="140">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column prop="amount_total" label="金额" min-width="120" align="right">
          <template #default="{ row }">{{ formatMoney(row.amount_total) }}</template>
        </el-table-column>
        <el-table-column label="状态" min-width="70" align="center">
          <template #default="{ row }">
            <span class="status-badge" :class="row.state === 'posted' ? 'success' : 'warning'">{{ row.state === 'posted' ? '已过账' : '草稿' }}</span>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-bar">
        <el-pagination v-model:current-page="pagination.page.value" v-model:page-size="pagination.pageSize.value" :total="pagination.total.value" :page-sizes="[10,20,50]" layout="total, sizes, prev, pager, next" @current-change="loadData" @size-change="pagination.onSizeChange" />
      </div>
    </el-card>

    <el-drawer v-model="drawerVisible" :title="detail ? `凭证 ${detail.id}` : '凭证详情'" size="600px">
      <template v-if="detail">
        <div class="jm-detail-top">
          <div class="jm-detail-row"><span class="jm-detail-label">凭证类型</span><span class="status-badge" :class="detail.state === 'posted' ? 'success' : 'warning'">{{ typeLabel(detail.move_type) }}</span></div>
          <div class="jm-detail-row"><span class="jm-detail-label">会计日期</span><span>{{ formatDate(detail.date) }}</span></div>
          <div class="jm-detail-row"><span class="jm-detail-label">创建时间</span><span>{{ formatDateTime(detail.created_at) }}</span></div>
          <div class="jm-detail-row"><span class="jm-detail-label">摘要</span><span>{{ detail.ref || '-' }}</span></div>
        </div>

        <el-table :data="detail.lines" stripe size="small" :summary-method="detailSummary" show-summary style="margin-top:16px;">
          <el-table-column prop="account_code" label="科目编码" min-width="110" />
          <el-table-column prop="account_name" label="科目名称" min-width="150" />
          <el-table-column label="借方" align="right" min-width="130">
            <template #default="{ row }">{{ formatMoney(row.debit) }}</template>
          </el-table-column>
          <el-table-column label="贷方" align="right" min-width="130">
            <template #default="{ row }">{{ formatMoney(row.credit) }}</template>
          </el-table-column>
        </el-table>
      </template>
      <div v-else class="jm-empty">加载中...</div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { getJournalMoves, getJournalMove } from '../api/finance'
import { formatMoney, formatDate, formatDateTime } from '../utils/format'
import { handleError } from '../api/index'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { useList } from '../composables/useList.js'

const { list, loading, filters, pagination, loadData, search } = useList({
  api: { getList: getJournalMoves },
  defaultFilters: { date_from: '', date_to: '', move_type: '' },
  buildParams: (f) => {
    const params = {}
    if (f.move_type) params.move_type = f.move_type
    if (f.date_from) params.date_from = f.date_from
    if (f.date_to) params.date_to = f.date_to
    return params
  },
  transform: (res) => ({ items: res.items || [], total: res.total || 0 }),
  onError: (e) => handleError(e, { defaultMsg: '加载凭证列表失败，请检查所选时间范围是否有凭证数据' })
})

const drawerVisible = ref(false)
const detail = ref(null)

const typeOptions = [
  { value: '', label: '全部' },
  { value: 'sale_order', label: '销售订单' },
  { value: 'purchase_order', label: '采购订单' },
  { value: 'receipt', label: '收款' },
  { value: 'payment', label: '付款' },
  { value: 'expense', label: '费用' },
  { value: 'depreciation', label: '计提折旧' },
  { value: 'asset_disposal', label: '资产处置' },
  { value: 'fixed_asset_purchase', label: '固定资产采购' },
  { value: 'opening_balance', label: '期初余额' },
  { value: 'cash_flow', label: '现金流' },
]

const typeLabel = (type) => {
  const map = {}
  for (const opt of typeOptions) map[opt.value] = opt.label
  return map[type] || type || '-'
}

const openDetail = async (row) => {
  drawerVisible.value = true
  detail.value = null
  try {
    detail.value = await getJournalMove(row.id)
  } catch (e) {
    handleError(e, { defaultMsg: '加载凭证详情失败，请检查凭证是否存在' })
    drawerVisible.value = false
  }
}

const detailSummary = ({ columns }) => {
  if (!detail.value) return columns.map(() => '')
  let totalDebit = 0, totalCredit = 0
  for (const line of detail.value.lines || []) {
    totalDebit += Number(line.debit || 0)
    totalCredit += Number(line.credit || 0)
  }
  return columns.map((col, idx) => {
    if (idx === 0) return '合计'
    if (idx === 2) return formatMoney(totalDebit)
    if (idx === 3) return formatMoney(totalCredit)
    return ''
  })
}

useAccountAwareData(() => search())
</script>

<style scoped>
.jm-table { cursor: pointer; }
.jm-empty { display: flex; align-items: center; justify-content: center; min-height: 200px; color: var(--text-secondary); }
.jm-detail-top { display: flex; flex-direction: column; gap: 8px; background: var(--bg-elevated); border-radius: 10px; padding: 14px 16px; }
.jm-detail-row { display: flex; align-items: center; gap: 12px; font-size: 14px; }
.jm-detail-label { font-size: 12px; color: var(--text-secondary); font-weight: 500; min-width: 70px; }
</style>
