<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">试算平衡表</span>
        </div>
      </template>

      <div class="filter-bar">
        <el-date-picker v-model="queryDate" type="date" placeholder="选择截止日期" value-format="YYYY-MM-DD" @change="loadData" />
        <el-button type="primary" @click="loadData" :disabled="!queryDate">查询</el-button>
      </div>

      <div v-if="dataLoaded" style="margin-bottom: 16px;">
        <el-tag v-if="balanced" type="success" effect="dark" size="large">✓ 借贷平衡</el-tag>
        <el-tag v-else type="danger" effect="dark" size="large">✗ 不平衡</el-tag>
        <span style="margin-left: 12px; font-size: 13px; color: var(--el-text-color-secondary);">
          借方合计: {{ formatMoney(totalDebit) }} &nbsp;|&nbsp; 贷方合计: {{ formatMoney(totalCredit) }}
        </span>
      </div>

      <el-table :data="rows" stripe v-loading="loading" :summary-method="summaryMethod" show-summary border>
        <template #empty><el-empty description="暂无数据" /></template>
        <el-table-column prop="account_code" label="科目编码" width="120" />
        <el-table-column prop="account_name" label="科目名称" min-width="200" />
        <el-table-column label="借方发生额" align="right" width="180">
          <template #default="{ row }">
            {{ formatMoney(row.debit) }}
          </template>
        </el-table-column>
        <el-table-column label="贷方发生额" align="right" width="180">
          <template #default="{ row }">
            {{ formatMoney(row.credit) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import dayjs from 'dayjs'
import { getTrialBalance } from '../api/finance'
import { formatMoney } from '../utils/format'
import { handleError } from '../api/index'
import { useAccountAwareData } from '../composables/useAccountAwareData'

const loading = ref(false)
const dataLoaded = ref(false)
const queryDate = ref(dayjs().format('YYYY-MM-DD'))

const rows = ref([])
const totalDebit = ref(0)
const totalCredit = ref(0)
const balanced = ref(false)

const loadData = async () => {
  if (!queryDate.value) return
  loading.value = true
  dataLoaded.value = false
  try {
    const res = await getTrialBalance({ date: queryDate.value })
    rows.value = res.rows || []
    totalDebit.value = Number(res.total_debit)
    totalCredit.value = Number(res.total_credit)
    balanced.value = res.balanced
    dataLoaded.value = true
  } catch (e) {
    handleError(e, { defaultMsg: '加载试算平衡表失败' })
  } finally {
    loading.value = false
  }
}

const summaryMethod = ({ columns }) => {
  return columns.map((col, idx) => {
    if (idx === 0) return '合计'
    if (idx === 2) return formatMoney(totalDebit.value)
    if (idx === 3) return formatMoney(totalCredit.value)
    return ''
  })
}

useAccountAwareData(loadData)
</script>

