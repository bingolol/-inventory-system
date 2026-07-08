<template>
  <div v-loading="loading">
    <div class="vat-top">
      <span v-if="taxReport" class="vat-taxpayer" :class="taxReport.taxpayer_type === 'small_scale' ? 'small' : 'general'">
        {{ taxReport.taxpayer_type === 'small_scale' ? '小规模纳税人' : '一般纳税人' }}
      </span>
      <el-radio-group v-model="reportType" @change="onReportTypeChange" size="small">
        <el-radio-button value="quarterly">按季度</el-radio-button>
        <el-radio-button value="monthly">按月份</el-radio-button>
      </el-radio-group>
    </div>

    <div v-if="reportType === 'quarterly'" class="filter-bar">
      <el-select v-model="queryForm.year" placeholder="年份" style="width:120px">
        <el-option v-for="year in years" :key="year" :label="year" :value="year" />
      </el-select>
      <el-select v-model="queryForm.quarter" placeholder="季度" style="width:120px">
        <el-option label="第一季度" value="1" />
        <el-option label="第二季度" value="2" />
        <el-option label="第三季度" value="3" />
        <el-option label="第四季度" value="4" />
      </el-select>
      <el-button type="primary" @click="getTaxReport">查询</el-button>
    </div>
    <div v-else class="filter-bar">
      <el-select v-model="monthlyForm.year" placeholder="年份" style="width:120px">
        <el-option v-for="year in years" :key="year" :label="year" :value="year" />
      </el-select>
      <el-select v-model="monthlyForm.month" placeholder="月份" style="width:120px">
        <el-option v-for="m in 12" :key="m" :label="m + '月'" :value="m" />
      </el-select>
      <el-button type="primary" @click="getMonthlyTaxReport">查询</el-button>
    </div>

    <div v-if="taxReport" class="vat-report">
      <div class="vat-report-title">
        <span v-if="reportType === 'quarterly'">{{ queryForm.year }}年第{{ queryForm.quarter }}季度增值税报表</span>
        <span v-else>{{ monthlyForm.year }}年{{ monthlyForm.month }}月增值税报表</span>
        <span class="vat-period">{{ taxReport.period_start }} ~ {{ taxReport.period_end }}</span>
      </div>

      <el-table :data="tableData" style="width:100%" :show-header="false">
        <el-table-column prop="item" label="项目" min-width="300">
          <template #default="scope">
            <span :class="['vat-item', {
              'vat-header': scope.row.isHeader,
              'vat-total': scope.row.isTotal,
              'vat-indent': scope.row.indent
            }]">
              <span v-if="scope.row.isHeader" class="vat-bullet">▸</span>
              {{ scope.row.item }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="value" label="金额" min-width="200" align="right">
          <template #default="scope">
            <span :class="['vat-amount', { 'vat-amount-total': scope.row.isTotal }]">
              {{ typeof scope.row.value === 'number' ? formatMoney(scope.row.value) : scope.row.value }}
            </span>
          </template>
        </el-table-column>
      </el-table>

      <div class="vat-invoice-summary">
        <div class="vat-inv-title">涉及发票</div>
        <div class="vat-inv-row">
          <div class="vat-inv-card">
            <span class="vat-inv-label">销项发票</span>
            <span class="vat-inv-count">{{ invoiceStats.outCount }} 张</span>
            <span class="vat-inv-amount">不含税 {{ formatMoney(invoiceStats.outAmount) }}</span>
          </div>
          <div class="vat-inv-card">
            <span class="vat-inv-label">进项发票</span>
            <span class="vat-inv-count">{{ invoiceStats.inCount }} 张</span>
            <span class="vat-inv-amount">不含税 {{ formatMoney(invoiceStats.inAmount) }}</span>
          </div>
          <div class="vat-inv-card vat-inv-link" @click="goToInvoices">
            <span class="vat-inv-label">查看全部发票 →</span>
            <span class="vat-inv-count">共 {{ invoiceStats.total }} 张</span>
          </div>
        </div>
      </div>
    </div>

    <el-empty v-else-if="!loading" description="请选择年份和季度后点击查询" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import invoicesApi from '../api/invoices'
import { formatMoney } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../utils/errorHandler'
import { currentYear, currentQuarter, generateYears, currentMonth } from '../utils/date'

const router = useRouter()

const reportType = ref('quarterly')
const queryForm = ref({ year: currentYear(), quarter: currentQuarter() })
const monthlyForm = ref({ year: currentYear(), month: Number(currentMonth().split('-')[1]) })
const years = ref([])
const taxReport = ref(null)
const loading = ref(false)

const buildYears = () => {
  years.value = generateYears(-2, 2)
}

const tableData = computed(() => {
  if (!taxReport.value) return []
  const r = taxReport.value
  if (r.taxpayer_type === 'small_scale') {
    return [
      { item: '一、计税依据', value: '', isHeader: true },
      { item: '应征增值税不含税销售额', value: r.output_total, indent: true },
      { item: '二、税款计算', value: '', isHeader: true },
      { item: '销项税额', value: r.output_tax, indent: true },
      { item: '进项税额', value: r.input_tax, indent: true },
      { item: '应纳税额合计', value: r.tax_payable, isTotal: true },
    ]
  }
  return [
    { item: '销项税额', value: r.output_tax },
    { item: '进项税额', value: r.input_tax },
    { item: '应纳税额合计', value: r.tax_payable, isTotal: true },
  ]
})

const invoiceStats = computed(() => {
  const list = taxReport.value?.invoice_list || []
  const out = list.filter(i => i.direction === 'out')
  const inn = list.filter(i => i.direction === 'in')
  return {
    total: list.length,
    outCount: out.length,
    inCount: inn.length,
    outAmount: out.reduce((s, i) => s + Number(i.amount_without_tax || 0), 0),
    inAmount: inn.reduce((s, i) => s + Number(i.amount_without_tax || 0), 0),
  }
})

const goToInvoices = () => router.push('/invoices')

const getTaxReport = async () => {
  loading.value = true
  try { taxReport.value = await invoicesApi.getTaxReport(queryForm.value.year, queryForm.value.quarter) }
  catch (e) { handleError(e, { defaultMsg: '获取税务报表失败，请检查所选季度是否有发票数据' }) }
  finally { loading.value = false }
}

const getMonthlyTaxReport = async () => {
  loading.value = true
  try { taxReport.value = await invoicesApi.getTaxReportMonthly(monthlyForm.value.year, monthlyForm.value.month) }
  catch (e) { handleError(e, { defaultMsg: '获取月度税务报表失败，请检查所选月份是否有发票数据' }) }
  finally { loading.value = false }
}

const onReportTypeChange = () => {
  taxReport.value = null
  if (reportType.value === 'quarterly') getTaxReport(); else getMonthlyTaxReport()
}

const fetchData = () => {
  if (reportType.value === 'quarterly') getTaxReport(); else getMonthlyTaxReport()
}

buildYears()
useAccountAwareData(fetchData)
</script>

<style scoped>
.vat-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.vat-taxpayer {
  padding: 4px 14px;
  border-radius: 9999px;
  font-size: 13px;
  font-weight: 600;
}
.vat-taxpayer.small { background: var(--primary-light); color: var(--primary); }
.vat-taxpayer.general { background: var(--danger-light); color: var(--danger); }

.vat-report {
  animation: vatFade 0.3s ease;
}
@keyframes vatFade {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
.vat-report-title {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 16px;
  font-weight: 700;
  color: var(--text-primary);
  margin: 16px 0;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-lighter);
}
.vat-period {
  font-size: 13px;
  font-weight: 400;
  color: var(--text-secondary);
}

.vat-item {
  font-size: 14px;
  color: var(--text-regular);
  padding: 4px 0;
  display: flex;
  align-items: center;
  gap: 6px;
}
.vat-header {
  font-weight: 700;
  color: var(--text-primary);
  font-size: 15px;
}
.vat-total {
  font-weight: 800;
  color: var(--primary);
  font-size: 17px;
  background: var(--primary-light);
  margin: 4px -12px;
  padding: 6px 12px;
  border-radius: 8px;
}
.vat-indent {
  padding-left: 24px;
  color: var(--text-secondary);
}
.vat-bullet {
  color: var(--primary);
  font-size: 12px;
}
.vat-amount {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 14px;
  color: var(--text-regular);
}
.vat-amount-total {
  font-weight: 800;
  font-size: 17px;
  color: var(--primary);
  background: var(--primary-light);
  padding: 2px 10px;
  border-radius: 6px;
  display: inline-block;
}

.vat-invoice-summary {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--border-lighter);
}
.vat-inv-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 12px;
}
.vat-inv-row {
  display: flex;
  gap: 12px;
}
.vat-inv-card {
  flex: 1;
  background: var(--bg-elevated);
  border: 1px solid var(--border-lighter);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.vat-inv-link {
  cursor: pointer;
  background: linear-gradient(135deg, var(--primary-light), var(--primary-light));
  border-color: var(--border-light);
  justify-content: center;
  align-items: center;
  text-align: center;
}
.vat-inv-link:hover {
  border-color: var(--primary);
}
.vat-inv-label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
}
.vat-inv-count {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary);
}
.vat-inv-amount {
  font-size: 13px;
  color: var(--text-regular);
}
.vat-inv-link .vat-inv-label {
  color: var(--primary);
  font-weight: 600;
  font-size: 13px;
}
</style>
