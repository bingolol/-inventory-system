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

      <div v-if="dataLoaded" class="tb-bar" :class="balanced ? 'tb-ok' : 'tb-err'">
        <div class="tb-bar-left">
          <span class="tb-icon">{{ balanced ? '✓' : '✗' }}</span>
          <span>{{ balanced ? '借贷平衡' : '借贷不平衡' }}</span>
        </div>
        <div class="tb-bar-right">
          <span>借方 {{ formatMoney(totalDebit) }}</span>
          <span class="tb-vs">=</span>
          <span>贷方 {{ formatMoney(totalCredit) }}</span>
        </div>
      </div>
      <div v-if="dataLoaded" class="tb-formula">
        所有科目借方发生额之和 = 所有科目贷方发生额之和，借贷必相等
        <template v-if="!balanced">，请检查凭证录入是否有误</template>
      </div>

      <el-table :data="rows" stripe v-loading="loading" :summary-method="summaryMethod" show-summary>
        <template #empty><el-empty description="暂无数据" /></template>
        <el-table-column prop="code" label="科目编码" min-width="120" />
        <el-table-column prop="name" label="科目名称" min-width="200" />
        <el-table-column label="借方发生额" align="right" min-width="180">
          <template #default="{ row }">{{ formatMoney(row.debit) }}</template>
        </el-table-column>
        <el-table-column label="贷方发生额" align="right" min-width="180">
          <template #default="{ row }">{{ formatMoney(row.credit) }}</template>
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
  loading.value = true; dataLoaded.value = false
  try {
    const res = await getTrialBalance({ date: queryDate.value })
    rows.value = res.rows || []; totalDebit.value = Number(res.total_debit)
    totalCredit.value = Number(res.total_credit); balanced.value = res.balanced
    dataLoaded.value = true
  } catch (e) {
    handleError(e, { defaultMsg: '加载试算平衡表失败，请检查所选日期是否有凭证数据' })
  } finally { loading.value = false }
}

const summaryMethod = ({ columns }) => columns.map((col, idx) => {
  if (idx === 0) return '合计'
  if (idx === 2) return formatMoney(totalDebit.value)
  if (idx === 3) return formatMoney(totalCredit.value)
  return ''
})

useAccountAwareData(loadData)
</script>

<style scoped>
.tb-bar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 10px 16px; border-radius: 10px; margin-bottom: 16px; font-size: 14px;
}
.tb-ok { background: #f0f9eb; color: #67c23a; }
.tb-err { background: #fef0f0; color: #f56c6c; }
.tb-bar-left { display: flex; align-items: center; gap: 8px; font-weight: 600; }
.tb-icon { font-size: 18px; font-weight: 700; }
.tb-bar-right { display: flex; align-items: center; gap: 8px; font-size: 13px; }
.tb-bar-right span { font-weight: 600; }
.tb-vs { color: #c9cdd4; font-weight: 400 !important; }
.tb-formula { font-size: 12px; color: #c9cdd4; text-align: center; margin-bottom: 16px; font-family: 'Consolas', 'Monaco', monospace; }
</style>
