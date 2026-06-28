<template>
  <div>
    <div class="bs-top">
      <el-date-picker v-model="reportDate" type="date" placeholder="选择日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" @change="loadBalanceSheet" style="width:160px" />
      <el-button type="primary" @click="loadBalanceSheet" :loading="loading">查询</el-button>
    </div>
    <div v-if="d" class="bs-body">
      <div class="bs-title">
        <span class="bs-title-text">资产负债表</span>
        <span class="bs-title-date">截至 {{ formatDate(reportDate) }}</span>
      </div>
      <div class="bs-cols">
        <div class="bs-col">
          <div class="bs-col-header">资 产</div>
          <div class="bs-table">
            <div class="bs-row bs-main"><span>流动资产：</span><span></span></div>
            <div class="bs-row"><span>货币资金</span><span class="bs-val">{{ formatMoney(d.monetary_funds) }}</span></div>
            <div class="bs-row"><span>应收账款</span><span class="bs-val">{{ formatMoney(d.accounts_receivable) }}</span></div>
            <div class="bs-row"><span>预付账款</span><span class="bs-val">{{ formatMoney(d.prepayments) }}</span></div>
            <div class="bs-row"><span>存货</span><span class="bs-val">{{ formatMoney(d.inventory) }}</span></div>
            <div class="bs-row bs-total"><span>流动资产合计</span><span>{{ formatMoney(d.total_current_assets) }}</span></div>
            <div class="bs-row bs-main" style="margin-top:8px;"><span>非流动资产：</span><span></span></div>
            <div class="bs-row"><span>固定资产原值</span><span class="bs-val">{{ formatMoney(d.fixed_assets_original) }}</span></div>
            <div class="bs-row"><span>减：累计折旧</span><span class="bs-val">{{ formatMoney(d.accumulated_depreciation) }}</span></div>
            <div class="bs-row"><span>固定资产净值</span><span class="bs-val">{{ formatMoney(d.fixed_assets_net) }}</span></div>
            <div class="bs-row"><span>无形资产原值</span><span class="bs-val">{{ formatMoney(d.intangible_assets_original) }}</span></div>
            <div class="bs-row"><span>减：累计摊销</span><span class="bs-val">{{ formatMoney(d.accumulated_amortization) }}</span></div>
            <div class="bs-row"><span>无形资产净值</span><span class="bs-val">{{ formatMoney(d.intangible_assets_net) }}</span></div>
            <div class="bs-row bs-total"><span>非流动资产合计</span><span>{{ formatMoney(d.total_non_current_assets) }}</span></div>
            <div class="bs-row bs-grand-total"><span>资产总计</span><span>{{ formatMoney(d.total_assets) }}</span></div>
          </div>
        </div>
        <div class="bs-col">
          <div class="bs-col-header">负债和所有者权益</div>
          <div class="bs-table">
            <div class="bs-row bs-main"><span>流动负债：</span><span></span></div>
            <div class="bs-row"><span>应付账款</span><span class="bs-val">{{ formatMoney(d.accounts_payable) }}</span></div>
            <div class="bs-row"><span>应交税费</span><span class="bs-val">{{ formatMoney(d.tax_payable) }}</span></div>
            <div class="bs-row bs-total"><span>流动负债合计</span><span>{{ formatMoney(d.total_current_liabilities) }}</span></div>
            <div class="bs-row bs-main" style="margin-top:8px;"><span>非流动负债：</span><span></span></div>
            <div class="bs-row"><span>长期借款</span><span class="bs-val">{{ formatMoney(d.long_term_borrowings) }}</span></div>
            <div class="bs-row bs-total"><span>非流动负债合计</span><span>{{ formatMoney(d.total_non_current_liabilities) }}</span></div>
            <div class="bs-row bs-total"><span>负债合计</span><span>{{ formatMoney(d.total_liabilities) }}</span></div>
            <div class="bs-row bs-main" style="margin-top:8px;"><span>所有者权益：</span><span></span></div>
            <div class="bs-row"><span>实收资本</span><span class="bs-val">{{ formatMoney(d.paid_in_capital) }}</span></div>
            <div class="bs-row"><span>未分配利润</span><span class="bs-val">{{ formatMoney(d.retained_earnings) }}</span></div>
            <div class="bs-row bs-total"><span>所有者权益合计</span><span>{{ formatMoney(d.total_equity) }}</span></div>
            <div class="bs-row bs-grand-total"><span>负债和所有者权益总计</span><span>{{ formatMoney(d.total_liabilities_and_equity) }}</span></div>
          </div>
        </div>
      </div>
      <el-alert :title="d.balanced ? '✓ 资产负债表平衡' : '⚠ 资产负债表不平衡'" :type="d.balanced ? 'success' : 'error'" show-icon :closable="false" style="margin-top:16px;" />
    </div>
    <div v-else style="padding:40px 0;"><el-empty description="暂无数据，请先设置期初余额并录入业务数据" /></div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import financeApi from '../api/finance'
import { formatMoney, formatDate } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../utils/errorHandler'

const props = defineProps({ date: { type: String, default: () => new Date().toISOString().split('T')[0] } })
const loading = ref(false)
const d = ref(null)
const reportDate = ref(props.date)

watch(() => props.date, (v) => { reportDate.value = v; loadBalanceSheet() })

const loadBalanceSheet = async () => {
  loading.value = true
  try { d.value = await financeApi.getBalanceSheet(reportDate.value) }
  catch (e) { handleError(e, { defaultMsg: '加载资产负债表失败，请检查期初余额是否已设置' }); d.value = null }
  finally { loading.value = false }
}

useAccountAwareData(load)
</script>

<style scoped>
.bs-top { display: flex; gap: 8px; margin-bottom: 16px; }
.bs-body { animation: bf 0.3s ease; }
@keyframes bf { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
.bs-title { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid #f0f0f0; }
.bs-title-text { font-size: 18px; font-weight: 700; color: #1d2129; }
.bs-title-date { font-size: 13px; color: #86909c; }
.bs-cols { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.bs-col-header { font-size: 14px; font-weight: 700; color: #4f6ef7; padding: 8px 0; margin-bottom: 4px; border-bottom: 2px solid #eef1ff; }
.bs-table { display: flex; flex-direction: column; }
.bs-row { display: flex; justify-content: space-between; padding: 6px 0; font-size: 13px; color: #4e5969; border-bottom: 1px solid #f5f5f5; }
.bs-main { font-weight: 700; color: #1d2129; font-size: 14px; border-bottom: none; }
.bs-val { font-family: 'Consolas', 'Monaco', monospace; }
.bs-total { font-weight: 700; color: #4f6ef7; font-size: 14px; border-bottom: 2px solid #eef1ff; padding: 8px 0; }
.bs-grand-total { font-weight: 800; color: #1d2129; font-size: 16px; border-bottom: none; padding: 10px 0; border-top: 2px solid #1d2129; margin-top: 4px; }
</style>
