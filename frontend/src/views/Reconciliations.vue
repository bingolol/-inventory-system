<template>
  <div class="reconciliations-page">
    <!-- 筛选区 -->
    <el-card class="filter-card" shadow="never">
      <el-form inline>
        <el-form-item label="对账类型">
          <el-radio-group v-model="filter.party_type">
            <el-radio-button value="supplier">供应商对账</el-radio-button>
            <el-radio-button value="customer">客户对账</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="开始日期">
          <el-date-picker v-model="filter.start_date" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="filter.end_date" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadReconciliations" :loading="loading">查询对账</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 汇总卡片 -->
    <el-row v-if="result.summary" :gutter="16" class="summary-row">
      <el-col :span="4">
        <el-statistic title="对方数量" :value="result.summary.partner_count" />
      </el-col>
      <el-col :span="4">
        <el-statistic title="期初欠款合计" :value="result.summary.total_opening" prefix="¥" />
      </el-col>
      <el-col :span="4">
        <el-statistic title="本期发生合计" :value="result.summary.total_current" prefix="¥" />
      </el-col>
      <el-col :span="4">
        <el-statistic title="已收/已付合计" :value="result.summary.total_paid" prefix="¥" />
      </el-col>
      <el-col :span="4">
        <el-statistic title="期末欠款合计" :value="result.summary.total_closing" prefix="¥" />
      </el-col>
      <el-col :span="4">
        <el-statistic title="发票金额合计" :value="result.summary.total_invoice" prefix="¥" />
      </el-col>
    </el-row>

    <!-- 对账汇总表格 -->
    <el-card v-if="result.items?.length" shadow="never" class="detail-card">
      <template #header>
        <div class="card-header">
          <span>对账汇总（{{ result.period_start }} 至 {{ result.period_end }}）</span>
          <el-tag v-if="result.party_type === 'supplier'" type="primary">供应商</el-tag>
          <el-tag v-else type="success">客户</el-tag>
        </div>
      </template>
      <el-table :data="result.items" stripe border style="width: 100%" @row-click="onRowClick">
        <el-table-column prop="partner_name" label="对方名称" min-width="150" />
        <el-table-column prop="opening_balance" label="期初欠款" width="110" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.opening_balance) }}</template>
        </el-table-column>
        <el-table-column prop="current_amount" label="本期发生" width="110" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.current_amount) }}</template>
        </el-table-column>
        <el-table-column prop="paid_amount" label="已收/已付" width="110" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.paid_amount) }}</template>
        </el-table-column>
        <el-table-column prop="closing_balance" label="期末欠款" width="110" align="right">
          <template #default="{ row }">
            <span :class="row.closing_balance > 0 ? 'text-danger' : ''">¥{{ formatMoney(row.closing_balance) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="invoice_amount" label="发票金额" width="110" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.invoice_amount) }}</template>
        </el-table-column>
        <el-table-column prop="order_count" label="单据数" width="80" align="center" />
        <el-table-column prop="unpaid_orders" label="未结清" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.unpaid_orders > 0" type="danger" size="small">{{ row.unpaid_orders }}</el-tag>
            <span v-else class="text-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <el-button type="primary" size="small" text @click.stop="showDetail(row)">明细</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 空状态 -->
    <el-empty v-else-if="!loading" description="暂无数据" />

    <!-- 明细抽屉 -->
    <el-drawer v-model="drawerVisible" :title="`${detailResult.partner_name} - 对账明细`" size="700px">
      <el-row :gutter="12" class="detail-summary">
        <el-col :span="8"><el-statistic title="期初欠款" :value="detailResult.opening_balance" prefix="¥" /></el-col>
        <el-col :span="8"><el-statistic title="本期发生" :value="detailResult.current_amount" prefix="¥" /></el-col>
        <el-col :span="8"><el-statistic title="期末欠款" :value="detailResult.closing_balance" prefix="¥" /></el-col>
      </el-row>
      <el-table :data="detailResult.items" stripe border size="small" style="margin-top: 16px">
        <el-table-column prop="date" label="日期" width="100" />
        <el-table-column prop="description" label="描述" min-width="160" />
        <el-table-column prop="amount" label="金额" width="100" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.amount) }}</template>
        </el-table-column>
        <el-table-column prop="payment_status" label="状态" width="80" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.payment_status === 'paid'" type="success" size="small">已结清</el-tag>
            <el-tag v-else-if="row.payment_status === 'unpaid'" type="danger" size="small">未结清</el-tag>
            <el-tag v-else-if="row.payment_status === 'invoice'" type="info" size="small">发票</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="has_invoice" label="有发票" width="60" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.has_invoice" type="success" size="small">有</el-tag>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column prop="notes" label="备注" min-width="120" show-overflow-tooltip />
      </el-table>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import commonApi, { formatMoney } from '../api/common'
import { useAccountAwareData } from '../composables/useAccountAwareData'

const loading = ref(false)
const drawerVisible = ref(false)

const filter = reactive({
  party_type: 'supplier',
  start_date: '',
  end_date: ''
})

const result = reactive({
  summary: null,
  items: []
})

const detailResult = reactive({
  partner_name: '',
  opening_balance: 0,
  current_amount: 0,
  closing_balance: 0,
  items: []
})

const loadReconciliations = async () => {
  if (!filter.start_date || !filter.end_date) {
    ElMessage.warning('请选择开始日期和结束日期')
    return
  }
  loading.value = true
  try {
    const data = await commonApi.getReconciliations({
      party_type: filter.party_type,
      start_date: filter.start_date,
      end_date: filter.end_date
    })
    Object.assign(result, data)
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '查询失败')
  } finally {
    loading.value = false
  }
}

const showDetail = async (row) => {
  if (!filter.start_date || !filter.end_date) {
    ElMessage.warning('请选择开始日期和结束日期')
    return
  }
  loading.value = true
  try {
    const data = await commonApi.getReconciliationDetail({
      party_type: filter.party_type,
      partner_id: row.partner_id,
      start_date: filter.start_date,
      end_date: filter.end_date
    })
    Object.assign(detailResult, data)
    drawerVisible.value = true
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '查询明细失败')
  } finally {
    loading.value = false
  }
}

const onRowClick = (row) => {
  showDetail(row)
}

// 默认本月
const setDefaultDates = () => {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  filter.start_date = `${y}-${m}-01`
  filter.end_date = `${y}-${m}-${new Date(y, now.getMonth() + 1, 0).getDate()}`
}

setDefaultDates()
useAccountAwareData(loadReconciliations)
</script>

<style scoped>
.filter-card {
  margin-bottom: 16px;
}
.summary-row {
  margin-bottom: 16px;
}
.detail-card {
  margin-bottom: 16px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.text-danger {
  color: #f56c6c;
}
.text-muted {
  color: #999;
}
.detail-summary {
  margin-bottom: 8px;
}
:deep(.el-table__row) {
  cursor: pointer;
}
</style>