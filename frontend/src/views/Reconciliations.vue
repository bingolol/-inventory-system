<template>
  <div>
    <div class="filter-bar" style="margin-bottom:16px;">
      <el-radio-group v-model="filter.party_type">
        <el-radio-button value="supplier">供应商对账</el-radio-button>
        <el-radio-button value="customer">客户对账</el-radio-button>
      </el-radio-group>
      <el-date-picker v-model="filter.start_date" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" />
      <el-date-picker v-model="filter.end_date" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" />
      <el-button type="primary" @click="loadReconciliations" :loading="loading">查询对账</el-button>
    </div>

    <div v-if="result.summary" class="rc-stats">
      <div class="rc-stat"><span class="rc-stat-label">对方数量</span><span class="rc-stat-value">{{ result.summary.partner_count }}</span></div>
      <div class="rc-stat"><span class="rc-stat-label">期初欠款</span><span class="rc-stat-value c-primary">{{ formatMoney(result.summary.total_opening) }}</span></div>
      <div class="rc-stat"><span class="rc-stat-label">本期发生</span><span class="rc-stat-value c-warning">{{ formatMoney(result.summary.total_current) }}</span></div>
      <div class="rc-stat"><span class="rc-stat-label">已收/已付</span><span class="rc-stat-value c-success">{{ formatMoney(result.summary.total_paid) }}</span></div>
      <div class="rc-stat"><span class="rc-stat-label">期末欠款</span><span class="rc-stat-value c-danger">{{ formatMoney(result.summary.total_closing) }}</span></div>
      <div class="rc-stat"><span class="rc-stat-label">发票金额</span><span class="rc-stat-value" style="color:#9b59b6;">{{ formatMoney(result.summary.total_invoice) }}</span></div>
    </div>

    <el-card v-if="result.items?.length" shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">对账汇总</span>
          <span class="status-badge" :class="result.party_type === 'supplier' ? 'primary' : 'success'">{{ result.party_type === 'supplier' ? '供应商' : '客户' }}</span>
        </div>
      </template>
      <el-table :data="result.items" stripe border style="width: 100%" @row-click="onRowClick">
        <el-table-column prop="partner_name" label="对方名称" min-width="150" />
        <el-table-column prop="opening_balance" label="期初欠款" min-width="110" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.opening_balance) }}</template>
        </el-table-column>
        <el-table-column prop="current_amount" label="本期发生" min-width="110" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.current_amount) }}</template>
        </el-table-column>
        <el-table-column prop="paid_amount" label="已收/已付" min-width="110" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.paid_amount) }}</template>
        </el-table-column>
        <el-table-column prop="closing_balance" label="期末欠款" min-width="110" align="right">
          <template #default="{ row }">
            <span :class="row.closing_balance > 0 ? 'text-danger' : ''">¥{{ formatMoney(row.closing_balance) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="invoice_amount" label="发票金额" min-width="110" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.invoice_amount) }}</template>
        </el-table-column>
        <el-table-column prop="order_count" label="单据数" min-width="80" align="center" />
        <el-table-column prop="unpaid_orders" label="未结清" min-width="80" align="center">
          <template #default="{ row }">
            <span class="status-badge danger" v-if="row.unpaid_orders > 0">{{ row.unpaid_orders }}</span>
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
        <el-table-column prop="date" label="日期" min-width="100" />
        <el-table-column prop="description" label="描述" min-width="160" />
        <el-table-column prop="amount" label="金额" min-width="100" align="right">
          <template #default="{ row }">¥{{ formatMoney(row.amount) }}</template>
        </el-table-column>
        <el-table-column prop="payment_status" label="状态" min-width="80" align="center">
          <template #default="{ row }">
            <span class="status-badge success" v-if="row.payment_status === 'paid'">已结清</span>
            <span class="status-badge danger" v-else-if="row.payment_status === 'unpaid'">未结清</span>
            <span class="status-badge info" v-else-if="row.payment_status === 'invoice'">发票</span>
          </template>
        </el-table-column>
        <el-table-column prop="has_invoice" label="有发票" min-width="60" align="center">
          <template #default="{ row }">
            <span class="status-badge success" v-if="row.has_invoice">有</span>
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
import commonApi from '../api/common'
import { formatMoney } from '../utils/format'
import { handleError } from '../api/index'
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
    handleError(err, { defaultMsg: '查询对账失败，请检查日期范围是否正确' })
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
    handleError(err, { defaultMsg: '查询明细失败，请检查选择的往来单位是否有数据' })
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
.rc-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}
.rc-stat {
  flex: 1;
  min-width: 140px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 12px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.rc-stat-label {
  font-size: 12px;
  color: #86909c;
  font-weight: 500;
  letter-spacing: 0.5px;
}
.rc-stat-value {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.5px;
}
.text-danger { color: #f56c6c; }
.text-muted { color: #999; }
.detail-summary { margin-bottom: 8px; }
:deep(.el-table__row) { cursor: pointer; }
</style>