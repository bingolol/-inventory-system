<template>
  <div>
    <div class="fs-top">
      <el-date-picker v-model="reportDate" type="date" placeholder="选择日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" @change="loadFinancialSummary" style="width:160px" />
      <el-button type="primary" @click="loadFinancialSummary" :loading="loading">查询</el-button>
    </div>
    <div v-if="financialSummary" class="fs-body">
      <div class="fs-cards">
        <div class="fs-card">
          <div class="fs-card-title" style="color:var(--primary);">资产状况</div>
          <div class="fs-row"><span class="fs-label">货币资金</span><span class="fs-value">{{ formatMoney(financialSummary.balance_sheet.monetary_funds) }}</span></div>
          <div class="fs-row"><span class="fs-label">应收账款</span><span class="fs-value">{{ formatMoney(financialSummary.balance_sheet.accounts_receivable) }}</span></div>
          <div class="fs-row"><span class="fs-label">库存价值</span><span class="fs-value">{{ formatMoney(financialSummary.balance_sheet.inventory) }}</span></div>
          <div class="fs-row fs-total"><span class="fs-label">资产总计</span><span class="fs-value">{{ formatMoney(financialSummary.balance_sheet.total_assets) }}</span></div>
        </div>
        <div class="fs-card">
          <div class="fs-card-title" style="color:var(--warning);">负债状况</div>
          <div class="fs-row"><span class="fs-label">应付账款</span><span class="fs-value">{{ formatMoney(financialSummary.balance_sheet.accounts_payable) }}</span></div>
          <div class="fs-row"><span class="fs-label">其他应付款</span><span class="fs-value">{{ formatMoney(financialSummary.balance_sheet.other_payable) }}</span></div>
          <div class="fs-row"><span class="fs-label">应交税费</span><span class="fs-value">{{ formatMoney(financialSummary.balance_sheet.tax_payable) }}</span></div>
          <div class="fs-row fs-total"><span class="fs-label">负债合计</span><span class="fs-value">{{ formatMoney(financialSummary.balance_sheet.total_liabilities) }}</span></div>
        </div>
        <div class="fs-card">
          <div class="fs-card-title" style="color:var(--success);">权益状况</div>
          <div class="fs-row"><span class="fs-label">未分配利润</span><span class="fs-value">{{ formatMoney(financialSummary.balance_sheet.retained_earnings) }}</span></div>
          <div class="fs-row fs-total"><span class="fs-label">权益合计</span><span class="fs-value">{{ formatMoney(financialSummary.balance_sheet.total_equity) }}</span></div>
        </div>
      </div>
      <div class="fs-health">
        <div class="fs-health-title">财务健康度</div>
        <div class="fs-health-cards">
          <div class="fs-h-item">
            <span class="fs-h-label">资产负债率</span>
            <span class="fs-h-value" :style="{ color: debtRatio < 50 ? 'var(--success)' : debtRatio < 70 ? 'var(--warning)' : 'var(--danger)' }">{{ debtRatio.toFixed(1) }}%</span>
            <span class="fs-h-tag" :class="debtRatio < 50 ? 'good' : debtRatio < 70 ? 'mid' : 'bad'">{{ debtRatio < 50 ? '健康' : debtRatio < 70 ? '注意' : '风险' }}</span>
          </div>
          <div class="fs-h-item">
            <span class="fs-h-label">流动比率</span>
            <span class="fs-h-value" :style="{ color: currentRatio > 2 ? 'var(--success)' : currentRatio > 1 ? 'var(--warning)' : 'var(--danger)' }">{{ currentRatio.toFixed(2) }}</span>
            <span class="fs-h-tag" :class="currentRatio > 2 ? 'good' : currentRatio > 1 ? 'mid' : 'bad'">{{ currentRatio > 2 ? '良好' : currentRatio > 1 ? '一般' : '紧张' }}</span>
          </div>
          <div class="fs-h-item">
            <span class="fs-h-label">权益比率</span>
            <span class="fs-h-value" :style="{ color: equityRatio > 50 ? 'var(--success)' : equityRatio > 30 ? 'var(--warning)' : 'var(--danger)' }">{{ equityRatio.toFixed(1) }}%</span>
            <span class="fs-h-tag" :class="equityRatio > 50 ? 'good' : equityRatio > 30 ? 'mid' : 'bad'">{{ equityRatio > 50 ? '稳健' : equityRatio > 30 ? '一般' : '偏低' }}</span>
          </div>
          <div class="fs-h-item">
            <span class="fs-h-label">期初余额状态</span>
            <span class="fs-h-value" style="font-size:14px;">{{ openingBalanceStatus.text }}</span>
            <span class="status-badge" :class="openingBalanceStatus.code">{{ openingBalanceStatus.text }}</span>
          </div>
        </div>
      </div>
    </div>
    <div v-else style="padding:40px 0;"><el-empty description="暂无数据，请先设置期初余额" /></div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import financeApi from '../api/finance'
import { formatMoney } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../api/index'
import { today } from '../utils/date'

const props = defineProps({ date: { type: String, default: () => today() } })
const loading = ref(false)
const financialSummary = ref(null)
const reportDate = ref(props.date)

watch(() => props.date, (d) => { reportDate.value = d; loadFinancialSummary() })

const loadFinancialSummary = async () => {
  loading.value = true
  try { financialSummary.value = await financeApi.getFinancialSummary(reportDate.value) }
  catch (e) { handleError(e, { defaultMsg: '加载财务汇总失败，请检查账套设置是否正确' }); financialSummary.value = null }
  finally { loading.value = false }
}

const debtRatio = computed(() => {
  if (!financialSummary.value) return 0
  const ta = financialSummary.value.balance_sheet.total_assets
  const tl = financialSummary.value.balance_sheet.total_liabilities
  return ta > 0 ? (tl / ta * 100) : 0
})
const currentRatio = computed(() => {
  if (!financialSummary.value) return 0
  const cl = financialSummary.value.balance_sheet.total_current_liabilities
  return cl > 0
    ? (financialSummary.value.balance_sheet.total_current_assets / cl) : 0
})
const equityRatio = computed(() => {
  if (!financialSummary.value) return 0
  const ta = financialSummary.value.balance_sheet.total_assets
  const te = financialSummary.value.balance_sheet.total_equity
  return ta > 0 ? (te / ta * 100) : 0
})
const openingBalanceStatus = computed(() => financialSummary.value?.opening_balance_exists
  ? { text: '已设置', code: 'success' } : { text: '未设置', code: 'warning' })

useAccountAwareData(loadFinancialSummary)
</script>

<style scoped>
.fs-top { display: flex; gap: 8px; margin-bottom: 16px; }
.fs-body { animation: fsFade 0.3s ease; }
@keyframes fsFade { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
.fs-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 20px; }
.fs-card { background: var(--bg-elevated); border: 1px solid var(--border-lighter); border-radius: 12px; padding: 20px; }
.fs-card-title { font-size: 15px; font-weight: 700; margin-bottom: 16px; padding-bottom: 10px; border-bottom: 2px solid var(--border-lighter); }
.fs-row { display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px; }
.fs-label { color: var(--text-secondary); }
.fs-value { font-weight: 600; color: var(--text-regular); font-family: 'Consolas', 'Monaco', monospace; }
.fs-total { border-top: 2px solid var(--border-light); margin-top: 10px; padding-top: 12px; }
.fs-total .fs-label { font-weight: 700; color: var(--text-primary); font-size: 14px; }
.fs-total .fs-value { font-weight: 800; color: var(--text-primary); font-size: 17px; }

.fs-health { background: var(--bg-card); border: 1px solid var(--border-lighter); border-radius: 12px; padding: 20px; }
.fs-health-title { font-size: 15px; font-weight: 600; color: var(--text-primary); margin-bottom: 16px; }
.fs-health-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; }
.fs-h-item { display: flex; flex-direction: column; gap: 6px; }
.fs-h-label { font-size: 12px; color: var(--text-secondary); font-weight: 500; }
.fs-h-value { font-size: 24px; font-weight: 700; letter-spacing: -0.5px; }
.fs-h-tag { display: inline-block; padding: 2px 10px; border-radius: 9999px; font-size: 12px; font-weight: 500; width: fit-content; }
.fs-h-tag.good { background: var(--success-light); color: var(--success); }
.fs-h-tag.mid { background: var(--warning-light); color: var(--warning); }
.fs-h-tag.bad { background: var(--danger-light); color: var(--danger); }
</style>
