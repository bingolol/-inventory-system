<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">往来管理</span>
          <div style="display:flex;gap:8px;align-items:center;">
            <el-radio-group v-model="partnerType" @change="onPartnerTypeChange">
              <el-radio value="customer">客户</el-radio>
              <el-radio value="supplier">供应商</el-radio>
            </el-radio-group>
          </div>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="对账汇总" name="summary">
          <div class="filter-bar" style="margin-bottom:16px;">
            <el-date-picker v-model="rcFilter.start_date" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" />
            <el-date-picker v-model="rcFilter.end_date" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" />
            <el-button type="primary" @click="loadReconciliations" :loading="rcLoading">查询对账</el-button>
          </div>

          <div v-if="rcResult.summary" class="rc-stats">
            <div class="rc-stat"><span class="rc-stat-label">对方数量</span><span class="rc-stat-value">{{ rcResult.summary.partner_count }}</span></div>
            <div class="rc-stat"><span class="rc-stat-label">期初欠款</span><span class="rc-stat-value c-primary">{{ formatMoney(rcResult.summary.total_opening) }}</span></div>
            <div class="rc-stat"><span class="rc-stat-label">本期发生</span><span class="rc-stat-value c-warning">{{ formatMoney(rcResult.summary.total_current) }}</span></div>
            <div class="rc-stat"><span class="rc-stat-label">已收/已付</span><span class="rc-stat-value c-success">{{ formatMoney(rcResult.summary.total_paid) }}</span></div>
            <div class="rc-stat"><span class="rc-stat-label">期末欠款</span><span class="rc-stat-value c-danger">{{ formatMoney(rcResult.summary.total_closing) }}</span></div>
            <div class="rc-stat"><span class="rc-stat-label">发票金额</span><span class="rc-stat-value" style="color:#9b59b6;">{{ formatMoney(rcResult.summary.total_invoice) }}</span></div>
          </div>

          <el-table v-if="rcResult.items?.length" :data="rcResult.items" stripe border style="width:100%" @row-click="onRowClick">
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
              <template #default="{ row }"><span :class="row.closing_balance>0?'text-danger':''">¥{{ formatMoney(row.closing_balance) }}</span></template>
            </el-table-column>
            <el-table-column prop="invoice_amount" label="发票金额" min-width="110" align="right">
              <template #default="{ row }">¥{{ formatMoney(row.invoice_amount) }}</template>
            </el-table-column>
            <el-table-column prop="order_count" label="单据数" min-width="80" align="center" />
            <el-table-column prop="unpaid_orders" label="未结清" min-width="80" align="center">
              <template #default="{ row }"><span class="status-badge danger" v-if="row.unpaid_orders>0">{{ row.unpaid_orders }}</span><span v-else class="text-muted">-</span></template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ row }"><el-button type="primary" size="small" text @click.stop="showDetail(row)">明细</el-button></template>
            </el-table-column>
          </el-table>
          <el-empty v-else-if="!rcLoading" description="暂无数据" />
        </el-tab-pane>

        <el-tab-pane label="账龄分析" name="aging">
          <div class="filter-bar">
            <el-select v-model="partnerId" placeholder="选择往来单位" filterable :disabled="!partners.length" style="width:240px;">
              <el-option v-for="p in partners" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
            <el-date-picker v-model="asOfDate" type="date" placeholder="截止日期" value-format="YYYY-MM-DD" />
            <el-button type="primary" @click="loadAging" :disabled="!partnerId">查询</el-button>
          </div>

          <div v-loading="agLoading">
            <template v-if="agResult">
              <div class="ag-balance"><span class="ag-balance-label">{{ partnerType==='customer'?'客户':'供应商' }}应收/应付余额</span><span class="ag-balance-value">¥{{ formatMoney(agResult.balance) }}</span></div>
              <el-table :data="agingRows" stripe style="margin-top:16px;">
                <template #empty><el-empty description="暂无账龄数据" /></template>
                <el-table-column prop="bucket" label="账龄区间" min-width="160" />
                <el-table-column label="金额" align="right" min-width="200">
                  <template #default="{ row }">{{ formatMoney(row.amount) }}</template>
                </el-table-column>
              </el-table>
            </template>
            <el-empty v-else-if="!agLoading" description="请选择往来单位后查询" />
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-drawer v-model="drawerVisible" :title="`${detailResult?.partner_name||''} - 对账明细`" size="700px">
      <div v-if="detailResult">
        <div style="display:flex;gap:12px;margin-bottom:16px;">
          <div style="flex:1;text-align:center;"><span style="font-size:12px;color:var(--text-secondary);display:block;">期初欠款</span><span style="font-size:18px;font-weight:700;">¥{{ formatMoney(detailResult.opening_balance) }}</span></div>
          <div style="flex:1;text-align:center;"><span style="font-size:12px;color:var(--text-secondary);display:block;">本期发生</span><span style="font-size:18px;font-weight:700;">¥{{ formatMoney(detailResult.current_amount) }}</span></div>
          <div style="flex:1;text-align:center;"><span style="font-size:12px;color:var(--text-secondary);display:block;">期末欠款</span><span style="font-size:18px;font-weight:700;">¥{{ formatMoney(detailResult.closing_balance) }}</span></div>
        </div>
        <el-table :data="detailResult.items" stripe border size="small">
          <el-table-column prop="date" label="日期" min-width="100" />
          <el-table-column prop="description" label="描述" min-width="160" />
          <el-table-column prop="amount" label="金额" min-width="100" align="right">
            <template #default="{ row }">¥{{ formatMoney(row.amount) }}</template>
          </el-table-column>
          <el-table-column prop="payment_status" label="状态" min-width="80" align="center">
            <template #default="{ row }"><span class="status-badge" :class="row.payment_status==='paid'?'success':'warning'">{{ row.payment_status }}</span></template>
          </el-table-column>
        </el-table>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import dayjs from 'dayjs'
import { getPartnerReceivable } from '../api/finance'
import { getCustomers, getSuppliers } from '../api/partners'
import { getReconciliations, getReconciliationDetail } from '../api/common'
import { formatMoney } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../utils/errorHandler'

const activeTab = ref('summary')
const partnerType = ref('customer')

// ── 对账汇总 ──
const rcFilter = ref({ start_date: dayjs().startOf('month').format('YYYY-MM-DD'), end_date: dayjs().format('YYYY-MM-DD') })
const rcResult = ref({})
const rcLoading = ref(false)
const drawerVisible = ref(false)
const detailResult = ref(null)

const loadReconciliations = async () => {
  rcLoading.value = true
  try {
    const res = await getReconciliations({ party_type: partnerType.value, start_date: rcFilter.value.start_date, end_date: rcFilter.value.end_date })
    rcResult.value = res || {}
  } catch (e) { handleError(e, { defaultMsg: '获取对账数据失败' }) }
  finally { rcLoading.value = false }
}

const onRowClick = (row) => {}
const showDetail = async (row) => {
  try {
    const res = await getReconciliationDetail({ party_type: partnerType.value, partner_id: row.partner_id, start_date: rcFilter.value.start_date, end_date: rcFilter.value.end_date })
    detailResult.value = res
    drawerVisible.value = true
  } catch (e) { handleError(e, { defaultMsg: '获取明细失败' }) }
}

// ── 账龄分析 ──
const partners = ref([])
const partnerId = ref(null)
const asOfDate = ref(dayjs().format('YYYY-MM-DD'))
const agResult = ref(null)
const agLoading = ref(false)

const agingRows = computed(() => {
  if (!agResult.value || !agResult.value.aging) return []
  return Object.entries(agResult.value.aging).map(([bucket, amount]) => ({
    bucket: AGING_BUCKET_LABELS[bucket] || bucket,
    amount: Number(amount),
  }))
})

const AGING_BUCKET_LABELS = {
  '0-30': '未逾期（0-30天）',
  '31-60': '31-60天',
  '61-90': '61-90天',
  '90+': '90天以上',
}

const loadPartners = async () => {
  partnerId.value = null
  agResult.value = null
  try {
    const api = partnerType.value === 'customer' ? getCustomers : getSuppliers
    const res = await api({ page_size: 1000 })
    partners.value = res.items || []
  } catch (e) { handleError(e, { defaultMsg: '加载往来单位列表失败' }) }
}

const onPartnerTypeChange = () => { loadPartners() }

const loadAging = async () => {
  if (!partnerId.value) return
  agLoading.value = true
  try {
    const res = await getPartnerReceivable(partnerId.value, { partner_type: partnerType.value, as_of_date: asOfDate.value })
    agResult.value = res
  } catch (e) { handleError(e, { defaultMsg: '加载账龄分析失败' }) }
  finally { agLoading.value = false }
}

useAccountAwareData(() => { loadReconciliations(); loadPartners() })
</script>

<style scoped>
.rc-stats { display:flex; gap:12px; margin-bottom:16px; flex-wrap:wrap; }
.rc-stat { flex:1; min-width:120px; background:var(--bg-card); border:1px solid var(--border-lighter); border-radius:10px; padding:12px 14px; text-align:center; }
.rc-stat-label { display:block; font-size:11px; color:var(--text-secondary); margin-bottom:4px; }
.rc-stat-value { font-size:20px; font-weight:700; }
.ag-balance { background:linear-gradient(135deg,var(--primary-light),var(--primary-light)); border:1px solid var(--border-light); border-radius:12px; padding:16px 20px; display:flex; justify-content:space-between; align-items:center; }
.ag-balance-label { font-size:14px; color:var(--text-regular); }
.ag-balance-value { font-size:24px; font-weight:700; color:var(--primary); }
.c-primary { color:var(--primary); } .c-warning { color:var(--warning); } .c-success { color:var(--success); } .c-danger { color:var(--danger); }
.text-danger { color:var(--danger); } .text-muted { color:var(--text-placeholder); }
</style>
