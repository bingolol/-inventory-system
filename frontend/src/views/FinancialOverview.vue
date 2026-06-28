<template>
  <div class="fo" v-loading="loading">
    <!-- Row 1 -->
    <div class="fo-row">
      <div class="fo-metric" style="border-left:3px solid #4f62c0;">
        <div class="fo-ml">别人欠我</div>
        <div class="fo-mv c-primary">{{ formatMoney(bs?.accounts_receivable || 0) }}</div>
        <div class="fo-ms">应收账款</div>
      </div>
      <div class="fo-metric" style="border-left:3px solid #f56c6c;">
        <div class="fo-ml">我欠别人</div>
        <div class="fo-mv c-danger">{{ formatMoney(bs?.accounts_payable || 0) }}</div>
        <div class="fo-ms">应付账款</div>
      </div>
      <div class="fo-metric" style="border-left:3px solid #67c23a;">
        <div class="fo-ml">本月净利润</div>
        <div class="fo-mv c-success">{{ formatMoney(income?.net_profit || 0) }}</div>
        <div class="fo-ms">收入 − 成本 − 费用</div>
      </div>
      <div class="fo-metric" style="border-left:3px solid #e6a23c;">
        <div class="fo-ml">库存资金</div>
        <div class="fo-mv c-warning">{{ formatMoney(inventory?.total_stock_value || 0) }}</div>
        <div class="fo-ms">{{ inventory?.total_quantity || 0 }} 件 · {{ alerts.length }} 项预警</div>
      </div>
    </div>

    <!-- Row 2: health -->
    <div class="fo-row">
      <div class="fo-metric" v-for="m in health" :key="m.label">
        <div class="fo-ml">{{ m.label }}</div>
        <div class="fo-mv" style="font-size:20px;display:flex;align-items:center;gap:8px;">
          <span :style="{ color: m.color }">{{ m.value }}</span>
          <span class="fo-badge" :class="m.bc">{{ m.tag }}</span>
        </div>
        <div class="fo-ms">{{ m.formula }}</div>
      </div>
    </div>

    <!-- Row 3: Balance sheet -->
    <div class="fo-bh"><span class="fo-bt">资产负债</span></div>
    <div class="fo-tri">
      <div class="fo-tc"><div class="fo-th" style="color:#4f62c0;">资产</div>
        <div class="fo-tr"><span>货币资金</span><span class="fo-tv">{{ formatMoney(bs?.monetary_funds || 0) }}</span></div>
        <div class="fo-tr"><span>应收账款</span><span class="fo-tv">{{ formatMoney(bs?.accounts_receivable || 0) }}</span></div>
        <div class="fo-tr"><span>存货</span><span class="fo-tv">{{ formatMoney(bs?.inventory || 0) }}</span></div>
        <div class="fo-tt"><span>资产总计</span><span>{{ formatMoney(bs?.total_assets || 0) }}</span></div>
      </div>
      <div class="fo-tc"><div class="fo-th" style="color:#e6a23c;">负债</div>
        <div class="fo-tr"><span>应付账款</span><span class="fo-tv">{{ formatMoney(bs?.accounts_payable || 0) }}</span></div>
        <div class="fo-tr"><span>应交税费</span><span class="fo-tv">{{ formatMoney(bs?.tax_payable || 0) }}</span></div>
        <div class="fo-tt"><span>负债合计</span><span>{{ formatMoney(bs?.total_liabilities || 0) }}</span></div>
      </div>
      <div class="fo-tc"><div class="fo-th" style="color:#67c23a;">权益</div>
        <div class="fo-tr"><span>实收资本</span><span class="fo-tv">{{ formatMoney(bs?.paid_in_capital || 0) }}</span></div>
        <div class="fo-tr"><span>未分配利润</span><span class="fo-tv">{{ formatMoney(bs?.retained_earnings || 0) }}</span></div>
        <div class="fo-tt"><span>权益合计</span><span>{{ formatMoney(bs?.total_equity || 0) }}</span></div>
      </div>
    </div>

    <!-- Row 4 -->
    <div class="fo-quad">
      <div class="fo-qb"><div class="fo-qh">增值税</div><div class="fo-qr"><span class="fo-ql">应纳税额</span><span class="fo-qv c-danger">{{ formatMoney(vatTax?.tax_payable || 0) }}</span></div></div>
      <div class="fo-qb"><div class="fo-qh">企业所得税</div><div class="fo-qr"><span class="fo-ql">应纳税额</span><span class="fo-qv c-warning">{{ formatMoney(incomeTax?.tax_amount || 0) }}</span></div></div>
      <div class="fo-qb"><div class="fo-qh">利润速览</div><div class="fo-qr"><span class="fo-ql">营业收入</span><span class="fo-qv">{{ formatMoney(income?.revenue || 0) }}</span></div><div class="fo-qr"><span class="fo-ql">净利润</span><span class="fo-qv c-success">{{ formatMoney(income?.net_profit || 0) }}</span></div></div>
      <div class="fo-qb"><div class="fo-qh">现金流量</div><div class="fo-qr"><span class="fo-ql">净现金流</span><span class="fo-qv" :class="(cashFlow?.net_cash_flow || 0) >= 0 ? 'c-success' : 'c-danger'">{{ formatMoney(cashFlow?.net_cash_flow || 0) }}</span></div></div>
    </div>

    <!-- Row 5: Recent expenses -->
    <div class="fo-bh" style="margin-top:16px;"><span class="fo-bt">近期费用</span><span class="fo-bl" @click="router.push('/expenses')">全部 →</span></div>
    <div class="fo-tbl-wrap" v-if="expList.length">
      <table class="fo-tbl">
        <tr><th style="width:16%;">日期</th><th style="width:14%;">类别</th><th style="width:18%;">金额</th><th>描述</th></tr>
        <tr v-for="e in expList.slice(0,5)" :key="e.id">
          <td>{{ formatDate(e.expense_date) }}</td><td><span class="fo-badge fo-bi">{{ e.category }}</span></td>
          <td style="color:#f56c6c;font-weight:600;">-{{ formatMoney(e.amount) }}</td><td style="color:#86909c;">{{ e.description || '-' }}</td>
        </tr>
      </table>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import financeApi from '../api/finance'
import productsApi from '../api/products'
import invoicesApi from '../api/invoices'
import expensesApi from '../api/expenses'
import { formatMoney, formatDate } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../utils/errorHandler'

const router = useRouter()
const loading = ref(false)
const reportDate = ref(new Date().toISOString().split('T')[0])
const summary = ref(null)
const income = ref(null)
const cashFlow = ref(null)
const alerts = ref([])
const vatTax = ref(null)
const incomeTax = ref(null)
const expList = ref([])

function getRange() {
  const d = new Date()
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  return { start: `${y}-${m}-01`, end: reportDate.value, month: d.getMonth() + 1, year: y }
}

const bs = computed(() => summary.value?.balance_sheet)

const health = computed(() => {
  if (!bs.value) return []
  const ta = bs.value.total_assets || 0
  const tl = bs.value.total_liabilities || 0
  const te = bs.value.total_equity || 0
  const ca = bs.value.total_current_assets || 0
  const dR = ta > 0 ? (tl / ta * 100) : 0
  const cR = tl > 0 ? (ca / tl) : 0
  const eR = ta > 0 ? (te / ta * 100) : 0
  const ob = summary.value?.opening_balance_exists
  return [
    { label: '资产负债率', value: dR.toFixed(1) + '%', color: dR < 50 ? '#67c23a' : dR < 70 ? '#e6a23c' : '#f56c6c', tag: dR < 50 ? '健康' : dR < 70 ? '注意' : '风险', bc: dR < 50 ? 's' : dR < 70 ? 'w' : 'd', formula: '总负债 ÷ 总资产 × 100%' },
    { label: '流动比率', value: cR.toFixed(2), color: cR > 2 ? '#67c23a' : cR > 1 ? '#e6a23c' : '#f56c6c', tag: cR > 2 ? '良好' : cR > 1 ? '一般' : '紧张', bc: cR > 2 ? 's' : cR > 1 ? 'w' : 'd', formula: '流动资产 ÷ 流动负债' },
    { label: '权益比率', value: eR.toFixed(1) + '%', color: eR > 50 ? '#67c23a' : eR > 30 ? '#e6a23c' : '#f56c6c', tag: eR > 50 ? '稳健' : eR > 30 ? '一般' : '偏低', bc: eR > 50 ? 's' : eR > 30 ? 'w' : 'd', formula: '所有者权益 ÷ 总资产 × 100%' },
    { label: '期初余额', value: ob ? '已设置' : '未设置', color: ob ? '#67c23a' : '#e6a23c', tag: ob ? '正常' : '需设置', bc: ob ? 's' : 'w', formula: '' },
  ]
})

async function loadAll() {
  loading.value = true
  const r = getRange()
  const q = Math.ceil((new Date().getMonth() + 1) / 3)
  try {
    const [s, inc, cf, al, vat, it, ex] = await Promise.all([
      financeApi.getFinancialSummary(reportDate.value).catch(() => null),
      financeApi.getIncomeStatement(r.start, r.end).catch(() => null),
      financeApi.getCashFlowStatement(r.start, r.end).catch(() => null),
      productsApi.getAlerts().catch(() => []),
      invoicesApi.getTaxReportMonthly(r.year, r.month).catch(() => null),
      invoicesApi.getIncomeTaxReport(r.year, q).catch(() => null),
      expensesApi.getExpenses({ year: r.year, limit: 100 }).catch(() => ({ items: [] })),
    ])
    summary.value = s; income.value = inc; cashFlow.value = cf
    alerts.value = Array.isArray(al) ? al : []; vatTax.value = vat; incomeTax.value = it
    expList.value = ex?.items || []
  } catch (e) { handleError(e, { defaultMsg: '加载财务数据失败' }) }
  finally { loading.value = false }
}

useAccountAwareData(loadAll)
</script>

<style scoped>
.fo { animation: ff 0.2s ease; }
@keyframes ff { from { opacity: 0; } to { opacity: 1; } }

.fo-row { display: flex; gap: 12px; margin-bottom: 14px; }
.fo-metric { flex: 1; background: #fff; border: 1px solid #edf0f5; border-radius: 10px; padding: 14px 16px; }
.fo-ml { font-size: 12px; color: #4e5969; font-weight: 500; margin-bottom: 4px; }
.fo-mv { font-size: 24px; font-weight: 700; letter-spacing: -0.5px; line-height: 1.2; margin-bottom: 2px; }
.fo-ms { font-size: 12px; color: #86909c; }
.fo-badge { display: inline-block; padding: 1px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }
.fo-badge.s { background: #f0f9eb; color: #67c23a; }
.fo-badge.w { background: #fdf6ec; color: #e6a23c; }
.fo-badge.d { background: #fef0f0; color: #f56c6c; }
.fo-bi { background: #f5f6f8; color: #86909c; }

.fo-bh { display: flex; justify-content: space-between; align-items: center; margin: 14px 0 10px; }
.fo-bt { font-size: 13px; font-weight: 600; color: #1d2129; }
.fo-bl { font-size: 12px; color: #86909c; cursor: pointer; }
.fo-bl:hover { color: #4f62c0; }

.fo-tri { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 14px; }
.fo-tc { background: #fff; border: 1px solid #edf0f5; border-radius: 10px; padding: 16px; }
.fo-th { font-size: 13px; font-weight: 600; margin-bottom: 10px; padding-bottom: 8px; border-bottom: 1px solid #f5f6f8; }
.fo-tr { display: flex; justify-content: space-between; padding: 4px 0; font-size: 13px; color: #4e5969; }
.fo-tv { font-weight: 600; }
.fo-tt { display: flex; justify-content: space-between; border-top: 1px solid #e0e0e0; margin-top: 6px; padding-top: 8px; font-weight: 700; font-size: 14px; }
.fo-tt span:last-child { color: #4f62c0; }

.fo-quad { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; }
.fo-qb { background: #fff; border: 1px solid #edf0f5; border-radius: 8px; padding: 12px 14px; }
.fo-qh { font-size: 12px; font-weight: 600; color: #86909c; margin-bottom: 6px; }
.fo-qr { display: flex; justify-content: space-between; font-size: 13px; padding: 2px 0; }
.fo-ql { color: #86909c; }
.fo-qv { font-weight: 700; }

.fo-tbl-wrap { overflow: hidden; border-radius: 8px; border: 1px solid #edf0f5; }
.fo-tbl { width: 100%; border-collapse: collapse; }
.fo-tbl th { text-align: left; padding: 9px 14px; font-size: 11px; font-weight: 600; color: #86909c; border-bottom: 1px solid #f5f6f8; background: #fff; }
.fo-tbl td { padding: 9px 14px; font-size: 13px; color: #4e5969; border-bottom: 1px solid #f8f9fa; background: #fff; }
.fo-tbl tr:last-child td { border: none; }
.fo-tbl tr:hover td { background: #fafbfc; }

.c-primary { color: #4f62c0; }
.c-danger { color: #f56c6c; }
.c-success { color: #67c23a; }
.c-warning { color: #e6a23c; }
</style>
