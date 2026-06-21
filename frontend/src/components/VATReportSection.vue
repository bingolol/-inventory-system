<template>
  <div class="vat-report-section" v-loading="loading">
    <!-- 纳税人类型标签 -->
    <div style="margin-bottom: 16px;">
      <el-tag v-if="taxReport" :type="taxReport.taxpayer_type === 'small_scale' ? 'info' : 'primary'" size="large">
        {{ taxReport.taxpayer_type === 'small_scale' ? '小规模纳税人' : '一般纳税人' }}
      </el-tag>
    </div>

    <!-- 月份/季度切换 -->
    <el-radio-group v-model="reportType" @change="onReportTypeChange" style="margin-bottom: 15px;">
      <el-radio value="quarterly">按季度</el-radio>
      <el-radio value="monthly">按月份</el-radio>
    </el-radio-group>

    <!-- 季度选择 -->
    <el-form v-if="reportType === 'quarterly'" :inline="true" :model="queryForm" class="filter-bar">
      <el-form-item label="年份">
        <el-select v-model="queryForm.year" placeholder="请选择年份" required>
          <el-option v-for="year in years" :key="year" :label="year" :value="year" />
        </el-select>
      </el-form-item>
      <el-form-item label="季度">
        <el-select v-model="queryForm.quarter" placeholder="请选择季度" required>
          <el-option label="第一季度" value="1" />
          <el-option label="第二季度" value="2" />
          <el-option label="第三季度" value="3" />
          <el-option label="第四季度" value="4" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="getTaxReport">查询</el-button>
      </el-form-item>
    </el-form>

    <!-- 月份选择 -->
    <el-form v-else :inline="true" :model="monthlyForm" class="filter-bar">
      <el-form-item label="年份">
        <el-select v-model="monthlyForm.year" placeholder="请选择年份" required>
          <el-option v-for="year in years" :key="year" :label="year" :value="year" />
        </el-select>
      </el-form-item>
      <el-form-item label="月份">
        <el-select v-model="monthlyForm.month" placeholder="请选择月份" required>
          <el-option v-for="m in 12" :key="m" :label="m + '月'" :value="m" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="getMonthlyTaxReport">查询</el-button>
      </el-form-item>
    </el-form>

    <!-- 报表内容 -->
    <el-card v-if="taxReport" class="report-card" shadow="hover">
      <template #header>
        <div class="report-header">
          <div class="header-title">
            <el-icon class="title-icon"><Document /></el-icon>
            <span v-if="reportType === 'quarterly'">{{ queryForm.year }}年第{{ queryForm.quarter }}季度增值税报表</span>
            <span v-else>{{ monthlyForm.year }}年{{ monthlyForm.month }}月增值税报表</span>
          </div>
          <span class="period-badge">{{ taxReport.period_start }} ~ {{ taxReport.period_end }}</span>
        </div>
      </template>

      <!-- 小规模纳税人模板 -->
      <div v-if="taxReport.taxpayer_type === 'small_scale'" class="report-body">
        <el-table 
          :data="smallScaleData" 
          class="financial-table"
          :show-header="false"
          stripe
          highlight-current-row
        >
          <el-table-column prop="item" label="项目" min-width="350">
            <template #default="scope">
              <div :class="['item-cell', {
                'section-header': scope.row.isHeader,
                'indent-level-1': !scope.row.isHeader && scope.row.item.startsWith('  '),
                'indent-level-2': !scope.row.isHeader && scope.row.item.startsWith('    ')
              }]">
                <span v-if="scope.row.isHeader" class="section-marker">▸</span>
                {{ scope.row.item.replace(/^ +/, '') }}
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="value" label="金额" width="220" align="right">
            <template #default="scope">
              <span :class="['amount-cell', {
                'header-value': scope.row.isHeader,
                'total-row': isTotalRow(scope.row.item)
              }]">
                {{ typeof scope.row.value === 'number' ? formatMoney(scope.row.value) : scope.row.value }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 一般纳税人模板 -->
      <div v-else class="report-body">
        <el-table 
          :data="generalData" 
          class="financial-table"
          :show-header="false"
          stripe
          highlight-current-row
        >
          <el-table-column prop="item" label="项目" min-width="350">
            <template #default="scope">
              <div class="item-cell general-item">{{ scope.row.item }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="value" label="金额" width="220" align="right">
            <template #default="scope">
              <span class="amount-cell general-amount">{{ formatMoney(scope.row.value) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 发票明细 -->
      <div class="invoice-section">
        <div class="section-divider">
          <span class="divider-text">发票明细清单</span>
        </div>
        <el-table 
          :data="taxReport.invoice_list" 
          class="invoice-table"
          stripe
          :row-class-name="invoiceRowClass"
        >
          <el-table-column prop="invoice_no" label="发票号码" width="140" fixed>
            <template #default="scope">
              <span class="invoice-no">{{ scope.row.invoice_no }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="direction" label="方向" width="90" align="center">
            <template #default="scope">
              <el-tag 
                :type="scope.row.direction === 'out' ? '' : 'success'"
                effect="light"
                size="small"
                class="direction-tag"
              >
                {{ scope.row.direction === 'out' ? '销项' : '进项' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="invoice_type" label="类型" width="90" align="center">
            <template #default="scope">
              <el-tag 
                :type="scope.row.invoice_type === 'special' ? 'warning' : 'info'"
                effect="plain"
                size="small"
              >
                {{ scope.row.invoice_type === 'special' ? '专票' : '普票' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="tax_rate" label="税率" width="80" align="center">
            <template #default="scope">
              <span class="rate-text">{{ (Number(scope.row.tax_rate) * 100).toFixed(0) }}%</span>
            </template>
          </el-table-column>
          <el-table-column prop="amount_without_tax" label="不含税金额" width="130" align="right">
            <template #default="scope">
              <span class="money-text">{{ formatMoney(scope.row.amount_without_tax) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="tax_amount" label="税额" width="110" align="right">
            <template #default="scope">
              <span class="tax-text">{{ formatMoney(scope.row.tax_amount) }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="counterparty_name" label="对方名称" min-width="150" />
          <el-table-column prop="issue_date" label="开票日期" width="120" align="center">
            <template #default="scope">
              <span class="date-text">{{ scope.row.issue_date }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>

    <el-empty v-else-if="!loading" description="请选择年份和季度后点击查询" />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Document } from '@element-plus/icons-vue'
import invoicesApi from '../api/invoices'
import { formatMoney } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'

// 报告类型: quarterly / monthly
const reportType = ref('quarterly')

// 季度查询表单
const queryForm = ref({
  year: new Date().getFullYear(),
  quarter: Math.floor((new Date().getMonth() + 3) / 3)
})

// 月份查询表单
const monthlyForm = ref({
  year: new Date().getFullYear(),
  month: new Date().getMonth() + 1
})

// 年份列表
const years = ref([])
// 税务报表
const taxReport = ref(null)
// 加载状态
const loading = ref(false)

// 生成年份列表
const generateYears = () => {
  const currentYear = new Date().getFullYear()
  for (let i = currentYear - 2; i <= currentYear + 2; i++) {
    years.value.push(i)
  }
}

// 小规模纳税人数据
const smallScaleData = computed(() => {
  if (!taxReport.value) return []
  const r = taxReport.value
  // 注：后端 TaxReport schema 仅返回基础字段
  // output_total: 销项不含税金额合计
  // output_tax: 销项税额合计
  // input_total: 进项不含税金额合计
  // input_tax: 进项税额合计
  // tax_payable: 应纳税额（销项税 - 进项税，>=0）
  return [
    { item: '一、计税依据', value: '', isHeader: true },
    { item: '  （一）应征增值税不含税销售额', value: r.output_total },
    { item: '二、税款计算', value: '', isHeader: true },
    { item: '  销项税额', value: r.output_tax },
    { item: '  进项税额', value: r.input_tax },
    { item: '  应纳税额合计', value: r.tax_payable }
  ]
})

// 一般纳税人数据
const generalData = computed(() => {
  if (!taxReport.value) return []
  return [
    {
      item: '销项税额',
      value: taxReport.value.output_tax
    },
    {
      item: '进项税额',
      value: taxReport.value.input_tax
    },
    {
      item: '应纳税额合计',
      value: taxReport.value.tax_payable
    }
  ]
})

// 获取季度税务报表
const getTaxReport = async () => {
  loading.value = true
  try {
    const response = await invoicesApi.getTaxReport(queryForm.value.year, queryForm.value.quarter)
    taxReport.value = response
  } catch (error) {
    console.error('获取税务报表失败:', error)
    ElMessage.error(error.response?.data?.detail || '获取税务报表失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

// 获取月度税务报表
const getMonthlyTaxReport = async () => {
  loading.value = true
  try {
    const response = await invoicesApi.getTaxReportMonthly(monthlyForm.value.year, monthlyForm.value.month)
    taxReport.value = response
  } catch (error) {
    console.error('获取月度税务报表失败:', error)
    ElMessage.error(error.response?.data?.detail || '获取月度税务报表失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

// 报告类型切换
const onReportTypeChange = () => {
  taxReport.value = null
  if (reportType.value === 'quarterly') {
    getTaxReport()
  } else {
    getMonthlyTaxReport()
  }
}

// 根据当前报告类型获取数据
const fetchData = () => {
  if (reportType.value === 'quarterly') {
    getTaxReport()
  } else {
    getMonthlyTaxReport()
  }
}

// 判断是否为合计行
const isTotalRow = (item) => {
  const totalKeywords = ['合计', '总计', '应纳税额合计', '附加税费合计']
  return totalKeywords.some(keyword => item.includes(keyword))
}

// 发票表格行样式
const invoiceRowClass = ({ row, rowIndex }) => {
  return ''
}

generateYears()
useAccountAwareData(fetchData)
</script>

<style scoped>
.vat-report-section {
  padding: 0;
}

/* ========== 报表卡片 ========== */
.report-card {
  margin-top: 16px;
  border-radius: 12px;
  border: 1px solid var(--el-border-color-lighter);
  transition: box-shadow 0.3s ease;
}

.report-card:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.06);
}

/* ========== 报表头部 ========== */
.report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.title-icon {
  font-size: 20px;
  color: var(--el-color-primary);
}

.period-badge {
  padding: 4px 12px;
  background: var(--el-fill-color-light);
  border-radius: 12px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

/* ========== 报表主体 ========== */
.report-body {
  margin-bottom: 24px;
}

.financial-table {
  --el-table-border-color: var(--el-border-color-lighter);
  --el-table-row-hover-bg-color: var(--el-fill-color-light);
}

.financial-table :deep(.el-table__row) {
  transition: background-color 0.2s ease;
}

.item-cell {
  padding: 8px 0;
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.section-header {
  font-weight: 600;
  color: var(--el-text-color-primary);
  background: var(--el-fill-color-light);
  padding: 10px 12px;
  margin: 4px -12px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.section-marker {
  color: var(--el-color-primary);
  font-size: 12px;
}

.indent-level-1 {
  padding-left: 20px;
}

.indent-level-2 {
  padding-left: 40px;
  color: var(--el-text-color-secondary);
}

.amount-cell {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.header-value {
  color: var(--el-text-color-placeholder);
  font-style: italic;
}

.total-row {
  font-weight: 600;
  color: var(--el-color-primary);
  font-size: 15px;
}

.general-item {
  font-weight: 500;
  padding: 8px 0;
}

.general-amount {
  font-weight: 600;
  color: var(--el-color-primary);
}

/* ========== 发票明细区域 ========== */
.invoice-section {
  margin-top: 24px;
}

.section-divider {
  display: flex;
  align-items: center;
  margin-bottom: 16px;
}

.section-divider::before,
.section-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: linear-gradient(to right, transparent, var(--el-border-color), transparent);
}

.divider-text {
  padding: 0 16px;
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}

.invoice-table {
  --el-table-border-color: var(--el-border-color-lighter);
  --el-table-row-hover-bg-color: var(--el-fill-color-light);
  border-radius: 8px;
  overflow: hidden;
}

.invoice-no {
  font-family: 'Consolas', 'Monaco', monospace;
  font-weight: 500;
  color: var(--el-text-color-primary);
}

.direction-tag {
  border-radius: 10px;
}

.rate-text {
  font-weight: 500;
  color: var(--el-color-warning);
}

.money-text {
  font-family: 'Consolas', 'Monaco', monospace;
  color: var(--el-text-color-regular);
}

.tax-text {
  font-family: 'Consolas', 'Monaco', monospace;
  font-weight: 600;
  color: var(--el-color-danger);
}

.date-text {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
</style>
