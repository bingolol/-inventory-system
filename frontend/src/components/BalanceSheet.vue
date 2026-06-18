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
        <div class="report-title">资产负债表</div>
        <div class="report-date">日期: {{ formatDate(reportDate) }}</div>
        
        <el-table :data="assetData" style="width: 100%" :show-header="false">
          <el-table-column prop="item" label="项目" width="300" />
          <el-table-column prop="amount" label="金额" width="200" align="right">
            <template #default="scope">
              <strong v-if="scope.row.isTotal">{{ formatMoney(scope.row.amount) }}</strong>
              <span v-else>{{ formatMoney(scope.row.amount) }}</span>
            </template>
          </el-table-column>
        </el-table>
        
        <el-divider />
        
        <el-table :data="liabilityEquityData" style="width: 100%" :show-header="false">
          <el-table-column prop="item" label="项目" width="300" />
          <el-table-column prop="amount" label="金额" width="200" align="right">
            <template #default="scope">
              <strong v-if="scope.row.isTotal">{{ formatMoney(scope.row.amount) }}</strong>
              <span v-else>{{ formatMoney(scope.row.amount) }}</span>
            </template>
          </el-table-column>
        </el-table>
        
        <el-divider />
        
        <div class="balance-check">
          <el-alert
            :title="balanceCheckMessage"
            :type="isBalanced ? 'success' : 'error'"
            show-icon
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
import financeApi from '../api/finance'
import { formatMoney } from '../api/common'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { formatDate } from '../utils/format'

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
    ElMessage.error('加载资产负债表失败')
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
  padding: 20px;
}

.report-content {
  padding: 20px;
}

.report-title {
  text-align: center;
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 10px;
}

.report-date {
  text-align: center;
  font-size: 16px;
  color: var(--text-regular);
  margin-bottom: 30px;
}

.balance-check {
  margin-top: 20px;
}

.no-data {
  text-align: center;
  padding: 40px;
}
</style>