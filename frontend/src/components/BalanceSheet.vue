<template>
  <div class="balance-sheet-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>资产负债表</span>
          <div class="header-actions">
            <el-date-picker
              v-model="reportDate"
              type="date"
              placeholder="选择日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              @change="loadBalanceSheet"
            />
            <el-button type="primary" @click="loadBalanceSheet" :loading="loading">刷新</el-button>
          </div>
        </div>
      </template>
      
      <div v-if="balanceSheet" class="report-content">
        <div class="report-title-section">
          <el-icon class="title-icon" :size="28"><DataLine /></el-icon>
          <h2 class="report-title">资产负债表</h2>
          <span class="report-date">截至 {{ formatDate(reportDate) }}</span>
        </div>
        
        <!-- 双列布局：资产 vs 负债和所有者权益 -->
        <el-row :gutter="20" class="dual-column-layout">
          <!-- 资产部分 -->
          <el-col :xs="24" :sm="24" :md="12" :lg="12">
            <div class="statement-section assets-section">
              <div class="section-header">
                <el-icon><TrendCharts /></el-icon>
                <span>资 产</span>
              </div>
              
              <el-table 
                :data="assetData" 
                class="statement-table"
                :show-header="false"
                stripe
                highlight-current-row
                max-height="600"
              >
                <el-table-column prop="item" label="项目" min-width="180">
                  <template #default="scope">
                    <div :class="['item-cell', {
                      'main-header': scope.row.isHeader,
                      'sub-header': scope.row.isSubHeader,
                      'total-row': scope.row.isTotal
                    }]">
                      {{ scope.row.item }}
                    </div>
                  </template>
                </el-table-column>
                <el-table-column prop="amount" label="金额" width="150" align="right">
                  <template #default="scope">
                    <span :class="['amount-cell', {
                      'total-amount': scope.row.isTotal
                    }]">
                      {{ formatMoney(scope.row.amount) }}
                    </span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-col>
          
          <!-- 负债和所有者权益部分 -->
          <el-col :xs="24" :sm="24" :md="12" :lg="12">
            <div class="statement-section liabilities-section">
              <div class="section-header">
                <el-icon><PieChart /></el-icon>
                <span>负债和所有者权益</span>
              </div>
              
              <el-table 
                :data="liabilityEquityData" 
                class="statement-table"
                :show-header="false"
                stripe
                highlight-current-row
                max-height="600"
              >
                <el-table-column prop="item" label="项目" min-width="180">
                  <template #default="scope">
                    <div :class="['item-cell', {
                      'main-header': scope.row.isHeader,
                      'sub-header': scope.row.isSubHeader,
                      'total-row': scope.row.isTotal
                    }]">
                      {{ scope.row.item }}
                    </div>
                  </template>
                </el-table-column>
                <el-table-column prop="amount" label="金额" width="150" align="right">
                  <template #default="scope">
                    <span :class="['amount-cell', {
                      'total-amount': scope.row.isTotal
                    }]">
                      {{ formatMoney(scope.row.amount) }}
                    </span>
                  </template>
                </el-table-column>
              </el-table>
            </div>
          </el-col>
        </el-row>
        
        <!-- 平衡检查 -->
        <div class="balance-check">
          <el-alert
            :title="balanceCheckMessage"
            :type="isBalanced ? 'success' : 'error'"
            show-icon
            :closable="false"
            class="balance-alert"
          />
        </div>
      </div>
      
      <div v-else class="no-data">
        <el-empty description="暂无数据，请先设置期初余额" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { handleError } from '../api/index'
import { DataLine, TrendCharts, PieChart } from '@element-plus/icons-vue'
import financeApi from '../api/finance'
import { formatMoney, formatDate } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'

const props = defineProps({
  date: {
    type: String,
    default: () => new Date().toISOString().split('T')[0]
  }
})

const loading = ref(false)
const balanceSheet = ref(null)
const reportDate = ref(props.date)

watch(() => props.date, (newDate) => {
  reportDate.value = newDate
  loadBalanceSheet()
})

const loadBalanceSheet = async () => {
  loading.value = true
  try {
    const response = await financeApi.getBalanceSheet(reportDate.value)
    balanceSheet.value = response
  } catch (error) {
    handleError(error, { defaultMsg: '加载资产负债表失败' })
    balanceSheet.value = null
  } finally {
    loading.value = false
  }
}



const assetData = computed(() => {
  if (!balanceSheet.value) return []
  
  const data = []
  data.push({ item: '资产', amount: 0, isHeader: true })
  data.push({ item: '流动资产:', amount: 0, isSubHeader: true })
  data.push({ item: '  货币资金', amount: balanceSheet.value.monetary_funds })
  data.push({ item: '  应收账款', amount: balanceSheet.value.accounts_receivable })
  data.push({ item: '  预付账款', amount: balanceSheet.value.prepayments })
  data.push({ item: '  存货', amount: balanceSheet.value.inventory })
  data.push({ item: '流动资产合计', amount: balanceSheet.value.total_current_assets, isTotal: true })
  data.push({ item: '非流动资产:', amount: 0, isSubHeader: true })
  data.push({ item: '  固定资产原值', amount: balanceSheet.value.fixed_assets_original })
  data.push({ item: '  减：累计折旧', amount: balanceSheet.value.accumulated_depreciation })
  data.push({ item: '  固定资产净值', amount: balanceSheet.value.fixed_assets_net })
  data.push({ item: '  无形资产原值', amount: balanceSheet.value.intangible_assets_original })
  data.push({ item: '  减：累计摊销', amount: balanceSheet.value.accumulated_amortization })
  data.push({ item: '  无形资产净值', amount: balanceSheet.value.intangible_assets_net })
  data.push({ item: '非流动资产合计', amount: balanceSheet.value.total_non_current_assets, isTotal: true })
  data.push({ item: '资产总计', amount: balanceSheet.value.total_assets, isTotal: true })
  
  return data
})

const liabilityEquityData = computed(() => {
  if (!balanceSheet.value) return []
  
  const data = []
  data.push({ item: '负债和所有者权益', amount: 0, isHeader: true })
  data.push({ item: '流动负债:', amount: 0, isSubHeader: true })
  data.push({ item: '  应付账款', amount: balanceSheet.value.accounts_payable })
  data.push({ item: '  应交税费', amount: balanceSheet.value.tax_payable })
  data.push({ item: '流动负债合计', amount: balanceSheet.value.total_current_liabilities, isTotal: true })
  data.push({ item: '非流动负债:', amount: 0, isSubHeader: true })
  data.push({ item: '  长期借款', amount: balanceSheet.value.long_term_borrowings })
  data.push({ item: '非流动负债合计', amount: balanceSheet.value.total_non_current_liabilities, isTotal: true })
  data.push({ item: '负债合计', amount: balanceSheet.value.total_liabilities, isTotal: true })
  data.push({ item: '所有者权益:', amount: 0, isSubHeader: true })
  data.push({ item: '  实收资本', amount: balanceSheet.value.paid_in_capital })
  data.push({ item: '  未分配利润', amount: balanceSheet.value.retained_earnings })
  data.push({ item: '所有者权益合计', amount: balanceSheet.value.total_equity, isTotal: true })
  data.push({ item: '负债和所有者权益总计', amount: balanceSheet.value.total_liabilities_and_equity, isTotal: true })
  
  return data
})

const isBalanced = computed(() => {
  if (!balanceSheet.value) return false
  const totalAssets = balanceSheet.value.total_assets
  const totalLiabilitiesAndEquity = balanceSheet.value.total_liabilities_and_equity
  return Math.abs(totalAssets - totalLiabilitiesAndEquity) < 0.01
})

const balanceCheckMessage = computed(() => {
  if (!balanceSheet.value) return ''
  const totalAssets = balanceSheet.value.total_assets
  const totalLiabilitiesAndEquity = balanceSheet.value.total_liabilities_and_equity
  const difference = totalAssets - totalLiabilitiesAndEquity
  
  if (Math.abs(difference) < 0.01) {
    return `资产负债表平衡 ✓ (资产总计: ${formatMoney(totalAssets)} = 负债和所有者权益总计: ${formatMoney(totalLiabilitiesAndEquity)})`
  } else {
    return `资产负债表不平衡 ✗ (差额: ${formatMoney(difference)})`
  }
})

useAccountAwareData(loadBalanceSheet)
</script>

<style scoped>
.balance-sheet-container {
  padding: 0;
}

/* ========== 报表内容区 ========== */
.report-content {
  padding: 24px;
}

/* ========== 标题区域 ========== */
.report-title-section {
  text-align: center;
  margin-bottom: 32px;
  padding-bottom: 20px;
  border-bottom: 2px solid var(--el-border-color-lighter);
}

.title-icon {
  color: var(--el-color-primary);
  margin-bottom: 8px;
}

.report-title {
  font-size: 26px;
  font-weight: 700;
  color: var(--el-text-color-primary);
  margin: 0 0 8px 0;
  letter-spacing: 2px;
}

.report-date {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

/* ========== 报表分区 ========== */
.dual-column-layout {
  margin-bottom: 24px;
}

.statement-section {
  height: 100%;
  border-radius: 10px;
  overflow: hidden;
  border: 1px solid var(--el-border-color-light);
  transition: box-shadow 0.3s ease;
  display: flex;
  flex-direction: column;
}

.statement-section:hover {
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
}

.assets-section {
  border-color: var(--el-color-success-light-7);
}

.liabilities-section {
  border-color: var(--el-color-warning-light-7);
}

.section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 20px;
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  flex-shrink: 0;
}

.assets-section .section-header {
  background: linear-gradient(135deg, var(--el-color-success), var(--el-color-success-light-3));
}

.liabilities-section .section-header {
  background: linear-gradient(135deg, var(--el-color-warning), var(--el-color-warning-light-3));
}

.section-header :deep(.el-icon) {
  font-size: 20px;
}

/* ========== 表格样式 ========== */
.statement-table {
  --el-table-border-color: var(--el-border-color-lighter);
  --el-table-row-hover-bg-color: var(--el-fill-color-light);
  flex: 1;
}

.statement-table :deep(.el-table__row) {
  transition: background-color 0.2s ease;
}

.item-cell {
  padding: 8px 12px;
  font-size: 13px;
  color: var(--el-text-color-regular);
}

.main-header {
  font-weight: 700;
  font-size: 14px;
  color: var(--el-text-color-primary);
  background: var(--el-fill-color);
  padding: 10px 12px;
  margin: 2px -12px;
  border-radius: 4px;
}

.sub-header {
  font-weight: 600;
  color: var(--el-text-color-primary);
  padding-left: 20px;
  background: var(--el-fill-color-light);
  margin: 2px -12px;
  padding: 8px 12px 8px 20px;
  border-radius: 4px;
  font-size: 13px;
}

.total-row {
  font-weight: 700;
  color: var(--el-color-primary);
  font-size: 14px;
  border-top: 1px dashed var(--el-border-color);
  padding-top: 10px;
  margin-top: 2px;
}

.amount-cell {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 13px;
  color: var(--el-text-color-regular);
  padding-right: 12px;
}

.total-amount {
  font-weight: 700;
  color: var(--el-color-primary);
  font-size: 14px;
}

/* ========== 平衡检查 ========== */
.balance-check {
  margin-top: 24px;
}

.balance-alert {
  border-radius: 8px;
}

.balance-alert :deep(.el-alert__title) {
  font-size: 14px;
  font-weight: 500;
}

/* ========== 无数据状态 ========== */
.no-data {
  text-align: center;
  padding: 60px 20px;
}
</style>