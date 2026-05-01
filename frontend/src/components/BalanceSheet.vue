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
            <el-button @click="exportReport">导出</el-button>
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
              <strong v-if="scope.row.isTotal">{{ scope.row.amount.toFixed(2) }}</strong>
              <span v-else>{{ scope.row.amount.toFixed(2) }}</span>
            </template>
          </el-table-column>
        </el-table>
        
        <el-divider />
        
        <el-table :data="liabilityEquityData" style="width: 100%" :show-header="false">
          <el-table-column prop="item" label="项目" width="300" />
          <el-table-column prop="amount" label="金额" width="200" align="right">
            <template #default="scope">
              <strong v-if="scope.row.isTotal">{{ scope.row.amount.toFixed(2) }}</strong>
              <span v-else>{{ scope.row.amount.toFixed(2) }}</span>
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
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api'

const props = defineProps({
  date: {
    type: String,
    default: () => new Date().toISOString().split('T')[0]
  }
})

const loading = ref(false)
const balanceSheet = ref(null)
const reportDate = ref(props.date)

const loadBalanceSheet = async () => {
  loading.value = true
  try {
    const response = await api.getBalanceSheet(reportDate.value)
    balanceSheet.value = response
  } catch (error) {
    ElMessage.error('加载资产负债表失败')
    balanceSheet.value = null
  } finally {
    loading.value = false
  }
}

const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

const assetData = computed(() => {
  if (!balanceSheet.value) return []
  
  const data = []
  data.push({ item: '资产', amount: 0, isHeader: true })
  data.push({ item: '流动资产:', amount: 0, isSubHeader: true })
  data.push({ item: '  现金', amount: balanceSheet.value.assets.current_assets.cash })
  data.push({ item: '  银行存款', amount: balanceSheet.value.assets.current_assets.bank })
  data.push({ item: '  应收账款', amount: balanceSheet.value.assets.current_assets.accounts_receivable })
  data.push({ item: '  库存', amount: balanceSheet.value.assets.current_assets.inventory })
  data.push({ item: '资产总计', amount: balanceSheet.value.assets.total_assets, isTotal: true })
  
  return data
})

const liabilityEquityData = computed(() => {
  if (!balanceSheet.value) return []
  
  const data = []
  data.push({ item: '负债和所有者权益', amount: 0, isHeader: true })
  data.push({ item: '负债:', amount: 0, isSubHeader: true })
  data.push({ item: '  应付账款', amount: balanceSheet.value.liabilities.current_liabilities.accounts_payable })
  data.push({ item: '  应交税费', amount: balanceSheet.value.liabilities.current_liabilities.tax_payable })
  data.push({ item: '负债合计', amount: balanceSheet.value.liabilities.total_liabilities, isTotal: true })
  data.push({ item: '所有者权益:', amount: 0, isSubHeader: true })
  data.push({ item: '  未分配利润', amount: balanceSheet.value.equity.retained_earnings })
  data.push({ item: '所有者权益合计', amount: balanceSheet.value.equity.total_equity, isTotal: true })
  data.push({ item: '负债和所有者权益总计', amount: balanceSheet.value.liabilities.total_liabilities + balanceSheet.value.equity.total_equity, isTotal: true })
  
  return data
})

const isBalanced = computed(() => {
  if (!balanceSheet.value) return false
  const totalAssets = balanceSheet.value.assets.total_assets
  const totalLiabilities = balanceSheet.value.liabilities.total_liabilities
  const totalEquity = balanceSheet.value.equity.total_equity
  return Math.abs(totalAssets - (totalLiabilities + totalEquity)) < 0.01
})

const balanceCheckMessage = computed(() => {
  if (!balanceSheet.value) return ''
  const totalAssets = balanceSheet.value.assets.total_assets
  const totalLiabilities = balanceSheet.value.liabilities.total_liabilities
  const totalEquity = balanceSheet.value.equity.total_equity
  const difference = totalAssets - (totalLiabilities + totalEquity)
  
  if (Math.abs(difference) < 0.01) {
    return `资产负债表平衡 ✓ (资产总计: ${totalAssets.toFixed(2)} = 负债和所有者权益总计: ${(totalLiabilities + totalEquity).toFixed(2)})`
  } else {
    return `资产负债表不平衡 ✗ (差额: ${difference.toFixed(2)})`
  }
})

const exportReport = () => {
  ElMessage.info('导出功能开发中...')
}

onMounted(() => {
  loadBalanceSheet()
})
</script>

<style scoped>
.balance-sheet-container {
  padding: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-actions {
  display: flex;
  gap: 10px;
  align-items: center;
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
  color: #666;
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