<template>
  <div class="financial-summary-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>财务汇总</span>
          <div class="header-actions">
            <el-date-picker
              v-model="reportDate"
              type="date"
              placeholder="选择日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              @change="loadFinancialSummary"
            />
            <el-button type="primary" @click="loadFinancialSummary" :loading="loading">刷新</el-button>
          </div>
        </div>
      </template>
      
      <div v-if="financialSummary" class="summary-content">
        <el-row :gutter="20">
          <el-col :span="8">
            <el-card shadow="hover" class="summary-card">
              <template #header>
                <div class="card-title">资产状况</div>
              </template>
              <div class="summary-item">
                <span class="label">货币资金:</span>
                <span class="value">{{ formatMoney(financialSummary.balance_sheet.monetary_funds) }}</span>
              </div>
              <div class="summary-item">
                <span class="label">应收账款:</span>
                <span class="value">{{ formatMoney(financialSummary.balance_sheet.accounts_receivable) }}</span>
              </div>
              <div class="summary-item">
                <span class="label">库存价值:</span>
                <span class="value">{{ formatMoney(financialSummary.balance_sheet.inventory) }}</span>
              </div>
              <div class="summary-item total">
                <span class="label">资产总计:</span>
                <span class="value">{{ formatMoney(financialSummary.balance_sheet.total_assets) }}</span>
              </div>
            </el-card>
          </el-col>
          
          <el-col :span="8">
            <el-card shadow="hover" class="summary-card">
              <template #header>
                <div class="card-title">负债状况</div>
              </template>
              <div class="summary-item">
                <span class="label">应付账款:</span>
                <span class="value">{{ formatMoney(financialSummary.balance_sheet.accounts_payable) }}</span>
              </div>
              <div class="summary-item">
                <span class="label">应交税费:</span>
                <span class="value">{{ formatMoney(financialSummary.balance_sheet.tax_payable) }}</span>
              </div>
              <div class="summary-item total">
                <span class="label">负债合计:</span>
                <span class="value">{{ formatMoney(financialSummary.balance_sheet.total_liabilities) }}</span>
              </div>
            </el-card>
          </el-col>
          
          <el-col :span="8">
            <el-card shadow="hover" class="summary-card">
              <template #header>
                <div class="card-title">权益状况</div>
              </template>
              <div class="summary-item">
                <span class="label">未分配利润:</span>
                <span class="value">{{ formatMoney(financialSummary.balance_sheet.retained_earnings) }}</span>
              </div>
              <div class="summary-item total">
                <span class="label">权益合计:</span>
                <span class="value">{{ formatMoney(financialSummary.balance_sheet.total_equity) }}</span>
              </div>
            </el-card>
          </el-col>
        </el-row>
        
        <el-row :gutter="20" style="margin-top: 20px;">
          <el-col :span="24">
            <el-card shadow="hover" class="summary-card">
              <template #header>
                <div class="card-title">财务健康度</div>
              </template>
              <el-row :gutter="20">
                <el-col :span="6">
                  <el-statistic title="资产负债率" :value="debtRatio" :precision="2" suffix="%">
                    <template #suffix>
                      <span :class="debtRatio < 50 ? 'healthy' : debtRatio < 70 ? 'warning' : 'danger'">
                        {{ debtRatio < 50 ? '健康' : debtRatio < 70 ? '注意' : '风险' }}
                      </span>
                    </template>
                  </el-statistic>
                </el-col>
                <el-col :span="6">
                  <el-statistic title="流动比率" :value="currentRatio" :precision="2">
                    <template #suffix>
                      <span :class="currentRatio > 2 ? 'healthy' : currentRatio > 1 ? 'warning' : 'danger'">
                        {{ currentRatio > 2 ? '良好' : currentRatio > 1 ? '一般' : '紧张' }}
                      </span>
                    </template>
                  </el-statistic>
                </el-col>
                <el-col :span="6">
                  <el-statistic title="权益比率" :value="equityRatio" :precision="2" suffix="%">
                    <template #suffix>
                      <span :class="equityRatio > 50 ? 'healthy' : equityRatio > 30 ? 'warning' : 'danger'">
                        {{ equityRatio > 50 ? '稳健' : equityRatio > 30 ? '一般' : '偏低' }}
                      </span>
                    </template>
                  </el-statistic>
                </el-col>
                <el-col :span="6">
                  <div class="status-statistic">
                    <div class="statistic-title">期初余额状态</div>
                    <div class="statistic-content">
                      <el-tag :type="openingBalanceStatus.type" size="large">
                        {{ openingBalanceStatus.text }}
                      </el-tag>
                    </div>
                  </div>
                </el-col>
              </el-row>
            </el-card>
          </el-col>
        </el-row>
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
const financialSummary = ref(null)
const reportDate = ref(props.date)

watch(() => props.date, (newDate) => {
  reportDate.value = newDate
  loadFinancialSummary()
})

const loadFinancialSummary = async () => {
  loading.value = true
  try {
    const response = await financeApi.getFinancialSummary(reportDate.value)
    financialSummary.value = response
  } catch (error) {
    ElMessage.error('加载财务汇总失败')
    financialSummary.value = null
  } finally {
    loading.value = false
  }
}



const debtRatio = computed(() => {
  if (!financialSummary.value) return 0
  const totalAssets = financialSummary.value.balance_sheet.total_assets
  const totalLiabilities = financialSummary.value.balance_sheet.total_liabilities
  return totalAssets > 0 ? (totalLiabilities / totalAssets * 100) : 0
})

const currentRatio = computed(() => {
  if (!financialSummary.value) return 0
  const currentAssets = financialSummary.value.balance_sheet.total_current_assets
  const currentLiabilities = financialSummary.value.balance_sheet.total_liabilities
  return currentLiabilities > 0 ? (currentAssets / currentLiabilities) : 0
})

const equityRatio = computed(() => {
  if (!financialSummary.value) return 0
  const totalAssets = financialSummary.value.balance_sheet.total_assets
  const totalEquity = financialSummary.value.balance_sheet.total_equity
  return totalAssets > 0 ? (totalEquity / totalAssets * 100) : 0
})

const openingBalanceStatus = computed(() => {
  if (!financialSummary.value) return { text: '未知', type: 'info' }
  return financialSummary.value.opening_balance_exists 
    ? { text: '已设置', type: 'success' } 
    : { text: '未设置', type: 'warning' }
})

useAccountAwareData(loadFinancialSummary)
</script>

<style scoped>
.financial-summary-container {
  padding: 20px;
}

.summary-content {
  padding: 20px;
}

.summary-card {
  margin-bottom: 20px;
}

.card-title {
  font-size: 18px;
  font-weight: bold;
}

.summary-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid var(--border-color);
}

.summary-item:last-child {
  border-bottom: none;
}

.summary-item.total {
  font-weight: bold;
  font-size: 16px;
  border-top: 2px solid var(--border-color);
  margin-top: 10px;
  padding-top: 10px;
}

.label {
  color: var(--text-secondary);
}

.value {
  font-weight: bold;
  color: var(--text-primary);
}

.healthy {
  color: var(--success);
  font-weight: bold;
}

.warning {
  color: var(--warning);
  font-weight: bold;
}

.danger {
  color: var(--danger);
  font-weight: bold;
}

.no-data {
  text-align: center;
  padding: 40px;
}

.status-statistic {
  text-align: center;
  padding: 8px 0;
}
.status-statistic .statistic-title {
  font-size: 12px;
  color: var(--text-secondary);
  margin-bottom: 8px;
}
.status-statistic .statistic-content {
  font-size: 20px;
  font-weight: bold;
}
</style>