<template>
  <div class="income-tax-report-section" v-loading="loading">
    <!-- 年份/季度选择 -->
    <el-form :inline="true" :model="queryForm" class="filter-bar">
      <el-form-item label="年份">
        <el-select v-model="queryForm.year" placeholder="请选择年份" required>
          <el-option v-for="year in years" :key="year" :label="year" :value="year" />
        </el-select>
      </el-form-item>
      <el-form-item label="季度">
        <el-select v-model="queryForm.quarter" placeholder="请选择季度" required>
          <el-option label="第一季度" :value="1" />
          <el-option label="第二季度" :value="2" />
          <el-option label="第三季度" :value="3" />
          <el-option label="第四季度" :value="4" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="getIncomeTaxReport">查询</el-button>
      </el-form-item>
    </el-form>

    <!-- 报表内容 -->
    <el-card v-if="incomeTaxReport" class="report-card" shadow="hover">
      <template #header>
        <div class="report-header">
          <div class="header-title">
            <el-icon class="title-icon"><TrendCharts /></el-icon>
            <span>{{ queryForm.year }}年第{{ queryForm.quarter }}季度企业所得税报表</span>
          </div>
          <el-tag type="warning" effect="plain" size="small">季度预缴申报</el-tag>
        </div>
      </template>

      <div class="report-body">
        <el-table 
          :data="reportData" 
          class="financial-table"
          :show-header="false"
          stripe
          highlight-current-row
        >
          <el-table-column prop="item" label="项目" min-width="400">
            <template #default="scope">
              <div :class="['item-cell', {
                'section-header': scope.row.isHeader,
                'indent-level-1': !scope.row.isHeader && scope.row.item.startsWith('  '),
                'total-highlight': isTotalItem(scope.row.item)
              }]">
                <span v-if="scope.row.isHeader" class="section-marker">▸</span>
                {{ scope.row.item.replace(/^ +/, '') }}
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="value" label="金额" width="240" align="right">
            <template #default="scope">
              <span :class="['amount-cell', {
                'empty-value': scope.row.value === '',
                'highlight-amount': isHighlightAmount(scope.row.item)
              }]">
                {{ typeof scope.row.value === 'number' ? formatMoney(scope.row.value) : scope.row.value }}
              </span>
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
import { TrendCharts } from '@element-plus/icons-vue'
import invoicesApi from '../api/invoices'
import { formatMoney } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'

// 获取当前季度
const getCurrentQuarter = () => Math.ceil((new Date().getMonth() + 1) / 3)

// 查询表单
const queryForm = ref({
  year: new Date().getFullYear(),
  quarter: getCurrentQuarter()
})

// 年份列表
const years = ref([])
// 企业所得税报表
const incomeTaxReport = ref(null)
// 加载状态
const loading = ref(false)

// 生成年份列表
const generateYears = () => {
  const currentYear = new Date().getFullYear()
  for (let i = currentYear - 3; i <= currentYear; i++) {
    years.value.push(i)
  }
}

// 报表数据（税务口径：发票说话）
const reportData = computed(() => {
  if (!incomeTaxReport.value) return []
  const r = incomeTaxReport.value
  // 后端 IncomeTaxReport schema 返回字段：
  // total_revenue: 销项发票不含税金额合计（税务口径收入）
  // total_cost: 进项发票不含税金额合计（税务口径成本）
  // operating_expenses: 有票费用合计（可税前扣除）
  // gross_profit: 毛利润 = total_revenue - total_cost
  // taxable_income: 应纳税所得额 = gross_profit - operating_expenses
  // tax_rate: 实际税率
  // tax_amount: 应纳企业所得税
  // invoice_revenue / invoice_cost / invoiced_expenses / non_invoice_expenses: 明细参考
  return [
    { item: '一、营业收入（税务口径）', value: r.total_revenue },
    { item: '  其中：销项发票不含税金额', value: r.invoice_revenue },
    { item: '二、营业成本（税务口径）', value: r.total_cost },
    { item: '  其中：进项发票不含税金额', value: r.invoice_cost },
    { item: '三、毛利润', value: r.gross_profit },
    { item: '四、减：有票费用（可税前扣除）', value: r.operating_expenses },
    { item: '  其中：无票费用（仅供参考）', value: r.non_invoice_expenses },
    { item: '五、应纳税所得额', value: r.taxable_income },
    { item: '六、税率', value: `${(Number(r.tax_rate) * 100).toFixed(2)}%` },
    { item: '七、应纳企业所得税', value: r.tax_amount }
  ]
})

// 判断是否为合计/关键项目
const isTotalItem = (item) => {
  const totalKeywords = ['合计', '总额', '实际利润额', '应纳所得税额', '实际应纳', '应补']
  return totalKeywords.some(keyword => item.includes(keyword))
}

// 判断是否需要高亮金额
const isHighlightAmount = (item) => {
  const highlightKeywords = ['利润总额', '实际利润额', '应纳所得税额', '实际应纳', '应补']
  return highlightKeywords.some(keyword => item.includes(keyword))
}

// 获取企业所得税报表
const getIncomeTaxReport = async () => {
  loading.value = true
  try {
    const response = await invoicesApi.getIncomeTaxReport(queryForm.value.year, queryForm.value.quarter)
    incomeTaxReport.value = response
  } catch (error) {
    console.error('获取企业所得税报表失败:', error)
    ElMessage.error(error.response?.data?.detail || '获取企业所得税报表失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

generateYears()
useAccountAwareData(getIncomeTaxReport)
</script>

<style scoped>
.income-tax-report-section {
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
  color: var(--el-color-warning);
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
  padding: 10px 0;
  font-size: 14px;
  color: var(--el-text-color-regular);
  transition: color 0.2s ease;
}

.section-header {
  font-weight: 600;
  color: var(--el-text-color-primary);
  background: linear-gradient(to right, var(--el-fill-color-light), transparent);
  padding: 10px 12px;
  margin: 4px -12px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.section-marker {
  color: var(--el-color-warning);
  font-size: 12px;
}

.indent-level-1 {
  padding-left: 24px;
  color: var(--el-text-color-secondary);
}

.total-highlight {
  font-weight: 600;
  color: var(--el-color-primary);
  font-size: 15px;
  border-top: 1px dashed var(--el-border-color);
  padding-top: 12px;
  margin-top: 4px;
}

.amount-cell {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 14px;
  color: var(--el-text-color-regular);
  transition: color 0.2s ease;
}

.empty-value {
  color: var(--el-text-color-placeholder);
  font-style: italic;
}

.highlight-amount {
  font-weight: 700;
  color: var(--el-color-primary);
  font-size: 15px;
}
</style>
