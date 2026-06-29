<template>
  <div>
    <div class="filter-bar" style="margin-bottom:16px;">
      <el-radio-group v-model="filter.party_type">
        <el-radio-button value="supplier">供应商对账</el-radio-button>
        <el-radio-button value="customer">客户对账</el-radio-button>
      </el-radio-group>
      <el-date-picker v-model="filter.start_date" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" />
      <el-date-picker v-model="filter.end_date" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" />
      <el-button type="primary" @click="loadData" :loading="loading">查询对账</el-button>
    </div>

    <div v-if="r?.summary" class="rc-stats">
      <div class="rc-stat"><span class="rc-stat-label">对方数量</span><span class="rc-stat-value">{{ r.summary.partner_count }}</span></div>
      <div class="rc-stat"><span class="rc-stat-label">期初欠款</span><span class="rc-stat-value" style="color:var(--primary);">{{ formatMoney(r.summary.total_opening) }}</span></div>
      <div class="rc-stat"><span class="rc-stat-label">本期发生</span><span class="rc-stat-value" style="color:var(--warning);">{{ formatMoney(r.summary.total_current) }}</span></div>
      <div class="rc-stat"><span class="rc-stat-label">已收/已付</span><span class="rc-stat-value" style="color:var(--success);">{{ formatMoney(r.summary.total_paid) }}</span></div>
      <div class="rc-stat"><span class="rc-stat-label">期末欠款</span><span class="rc-stat-value" style="color:var(--danger);">{{ formatMoney(r.summary.total_closing) }}</span></div>
      <div class="rc-stat"><span class="rc-stat-label">发票金额</span><span class="rc-stat-value" style="color:#9b59b6;">{{ formatMoney(r.summary.total_invoice) }}</span></div>
    </div>

    <el-table v-if="r?.items?.length" :data="r.items" stripe style="width:100%">
      <el-table-column prop="partner_name" label="对方名称" min-width="150" />
      <el-table-column prop="opening_balance" label="期初欠款" min-width="100" align="right">
        <template #default="{ row }">¥{{ formatMoney(row.opening_balance) }}</template>
      </el-table-column>
      <el-table-column prop="current_amount" label="本期发生" min-width="100" align="right">
        <template #default="{ row }">¥{{ formatMoney(row.current_amount) }}</template>
      </el-table-column>
      <el-table-column prop="paid_amount" label="已收/已付" min-width="100" align="right">
        <template #default="{ row }">¥{{ formatMoney(row.paid_amount) }}</template>
      </el-table-column>
      <el-table-column prop="closing_balance" label="期末欠款" min-width="100" align="right">
        <template #default="{ row }"><span :style="{ color: row.closing_balance > 0 ? 'var(--danger)' : 'var(--success)', fontWeight:600 }">¥{{ formatMoney(row.closing_balance) }}</span></template>
      </el-table-column>
      <el-table-column prop="invoice_amount" label="发票金额" min-width="100" align="right">
        <template #default="{ row }">¥{{ formatMoney(row.invoice_amount) }}</template>
      </el-table-column>
      <el-table-column prop="order_count" label="单据数" min-width="70" align="center" />
      <el-table-column prop="unpaid_orders" label="未结清" min-width="70" align="center">
        <template #default="{ row }"><span class="status-badge danger" v-if="row.unpaid_orders > 0">{{ row.unpaid_orders }}</span><span v-else style="color:var(--text-placeholder);">-</span></template>
      </el-table-column>
    </el-table>
    <el-empty v-else-if="!loading" description="请选择类型和日期后查询" />
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { getReconciliations } from '../api/common'
import { formatMoney } from '../utils/format'
import { handleError } from '../utils/errorHandler'

const loading = ref(false)
const r = ref(null)
const filter = reactive({ party_type: 'supplier', start_date: '', end_date: '' })

const loadData = async () => {
  loading.value = true
  try { r.value = await getReconciliations(filter) }
  catch (e) { handleError(e, { defaultMsg: '查询对账失败，请检查日期范围是否正确' }) }
  finally { loading.value = false }
}
</script>

<style scoped>
.rc-stats { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 16px; }
.rc-stat { flex: 1; min-width: 140px; background: var(--bg-elevated); border: 1px solid var(--border-lighter); border-radius: 12px; padding: 14px 16px; display: flex; flex-direction: column; gap: 4px; }
.rc-stat-label { font-size: 12px; color: var(--text-secondary); font-weight: 500; letter-spacing: 0.5px; }
.rc-stat-value { font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }
</style>
