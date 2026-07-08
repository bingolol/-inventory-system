<template>
  <div v-loading="loading">
    <div class="filter-bar">
      <el-select v-model="queryForm.year" placeholder="年份" style="width:120px">
        <el-option v-for="year in years" :key="year" :label="year" :value="year" />
      </el-select>
      <el-select v-model="queryForm.quarter" placeholder="季度" style="width:120px">
        <el-option label="第一季度" :value="1" />
        <el-option label="第二季度" :value="2" />
        <el-option label="第三季度" :value="3" />
        <el-option label="第四季度" :value="4" />
      </el-select>
      <el-button type="primary" @click="getReport">查询</el-button>
    </div>

    <div v-if="r" class="it-page">
      <div class="it-hero">
        <div class="it-hero-top">
          <div class="it-hero-title">企业所得税</div>
          <span class="it-period">{{ queryForm.year }}年第{{ queryForm.quarter }}季度</span>
        </div>
        <div class="it-hero-main">
          <div class="it-hero-number">
            <span class="it-hero-label">应纳企业所得税</span>
            <span class="it-hero-value">{{ formatMoney(r.tax_amount) }}</span>
          </div>
          <div class="it-hero-rate">
            <span>税率</span>
            <strong>{{ (Number(r.tax_rate) * 100).toFixed(1) }}%</strong>
          </div>
        </div>
      </div>

      <div class="it-waterfall">
        <div class="it-step it-step-positive">
          <div class="it-step-line"></div>
          <div class="it-step-body">
            <span class="it-step-label">营业收入</span>
            <span class="it-step-value">+ {{ formatMoney(r.total_revenue) }}</span>
          </div>
        </div>
        <div class="it-step it-step-negative">
          <div class="it-step-line"></div>
          <div class="it-step-body">
            <span class="it-step-label">营业成本</span>
            <span class="it-step-value">- {{ formatMoney(r.total_cost) }}</span>
          </div>
        </div>
        <div class="it-step it-step-inter">
          <div class="it-step-line"></div>
          <div class="it-step-body">
            <span class="it-step-label">毛利润</span>
            <span class="it-step-value">{{ formatMoney(r.gross_profit) }}</span>
          </div>
        </div>
        <div class="it-step it-step-negative">
          <div class="it-step-line"></div>
          <div class="it-step-body">
            <span class="it-step-label">减：可税前扣除费用</span>
            <span class="it-step-value">- {{ formatMoney(r.operating_expenses) }}</span>
          </div>
        </div>
        <div class="it-step it-step-final">
          <div class="it-step-line"></div>
          <div class="it-step-body">
            <span class="it-step-label">应纳税所得额</span>
            <span class="it-step-value">{{ formatMoney(r.taxable_income) }}</span>
          </div>
        </div>
        <div class="it-step it-step-result">
          <div class="it-step-line"></div>
          <div class="it-step-body">
            <span class="it-step-label">应纳企业所得税</span>
            <span class="it-step-value">{{ formatMoney(r.tax_amount) }}</span>
          </div>
        </div>
      </div>

      <div class="it-note">按会计准则口径计算 · 数据来自总账利润表</div>
    </div>

    <el-empty v-else-if="!loading" description="选择年份和季度后点击查询" />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import invoicesApi from '../api/invoices'
import { formatMoney } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../utils/errorHandler'
import { currentYear, currentQuarter, generateYears } from '../utils/date'

const queryForm = ref({ year: currentYear(), quarter: currentQuarter() })
const years = ref([])
const r = ref(null)
const loading = ref(false)

const genYears = () => {
  years.value = generateYears(-3, 0)
}

const getReport = async () => {
  loading.value = true
  try { r.value = await invoicesApi.getIncomeTaxReport(queryForm.value.year, queryForm.value.quarter) }
  catch (e) { handleError(e, { defaultMsg: '获取所得税报表失败，请检查所选季度是否有收入数据' }) }
  finally { loading.value = false }
}

genYears()
useAccountAwareData(getReport)
</script>

<style scoped>
.it-page { animation: itFade 0.3s ease; margin-top: 16px; }
@keyframes itFade { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

.it-hero {
  background: linear-gradient(135deg, #1a1a2e, #16213e);
  border-radius: 16px;
  padding: 24px 28px;
  color: var(--bg-card);
}
.it-hero-top {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 20px;
}
.it-hero-title { font-size: 18px; font-weight: 700; }
.it-period { font-size: 13px; padding: 4px 14px; background: rgba(255,255,255,0.1); border-radius: 9999px; }
.it-hero-main { display: flex; align-items: flex-end; gap: 24px; }
.it-hero-number { flex: 1; }
.it-hero-label { font-size: 13px; color: rgba(255,255,255,0.5); display: block; margin-bottom: 4px; }
.it-hero-value { font-size: 36px; font-weight: 700; letter-spacing: -1px; }
.it-hero-rate { font-size: 13px; color: rgba(255,255,255,0.5); padding: 8px 16px; background: rgba(255,255,255,0.06); border-radius: 10px; display: flex; flex-direction: column; align-items: center; gap: 4px; }
.it-hero-rate strong { font-size: 20px; color: var(--bg-card); }

.it-waterfall {
  margin-top: 20px;
  background: var(--bg-card);
  border-radius: 16px;
  border: 1px solid var(--border-lighter);
  padding: 8px 0;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
}
.it-step {
  display: flex;
  align-items: stretch;
  padding: 0;
}
.it-step-line {
  width: 4px;
  flex-shrink: 0;
  margin: 0 20px;
  border-radius: 2px;
}
.it-step-positive .it-step-line { background: var(--success); }
.it-step-negative .it-step-line { background: var(--danger); }
.it-step-inter .it-step-line { background: var(--warning); }
.it-step-final .it-step-line { background: var(--primary); }
.it-step-result .it-step-line { background: linear-gradient(180deg, var(--primary), #6366f1); }

.it-step-body {
  flex: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px 14px 0;
  border-bottom: 1px solid var(--border-lighter);
  font-size: 15px;
}
.it-step:last-child .it-step-body { border-bottom: none; }
.it-step-label { color: var(--text-regular); }
.it-step-value { font-weight: 700; font-family: 'Consolas', 'Monaco', monospace; }
.it-step-positive .it-step-value { color: var(--success); }
.it-step-negative .it-step-value { color: var(--danger); }
.it-step-final .it-step-value { color: var(--primary); font-size: 16px; }
.it-step-result .it-step-value { color: var(--bg-card); font-size: 18px; }
.it-step-result .it-step-body { background: linear-gradient(135deg, var(--primary), #6366f1); border-radius: 10px; margin: 4px 4px 4px 0; padding: 16px 20px; }
.it-step-result .it-step-label { color: rgba(255,255,255,0.7); }

.it-note {
  text-align: center;
  font-size: 13px;
  color: var(--text-placeholder);
  margin-top: 16px;
}
</style>
