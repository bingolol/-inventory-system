<template>
  <div class="income-statement-container">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>利润表</span>
          <div class="header-actions">
            <el-date-picker
              v-model="startDate"
              type="date"
              placeholder="开始日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              @change="loadIncomeStatement"
            />
            <span>至</span>
            <el-date-picker
              v-model="endDate"
              type="date"
              placeholder="结束日期"
              format="YYYY-MM-DD"
              value-format="YYYY-MM-DD"
              @change="loadIncomeStatement"
            />
            <el-button type="primary" @click="loadIncomeStatement" :loading="loading">刷新</el-button>
            <el-button @click="exportReport">导出</el-button>
          </div>
        </div>
      </template>
      
      <div v-if="incomeStatement" class="report-content">
        <div class="report-title">利润表（经营口径）</div>
        <div class="report-period">期间: {{ formatDate(startDate) }} 至 {{ formatDate(endDate) }}</div>
        
        <el-table :data="incomeData" style="width: 100%" :show-header="false">
          <el-table-column prop="item" label="项目" width="400" />
          <el-table-column prop="amount" label="金额" width="200" align="right">
            <template #default="scope">
              <strong v-if="scope.row.isTotal">{{ formatMoney(scope.row.amount) }}</strong>
              <span v-else>{{ formatMoney(scope.row.amount) }}</span>
            </template>
          </el-table-column>
        </el-table>
        
        <el-divider />
        
        <div class="profit-summary">
          <el-row :gutter="20">
            <el-col :span="8">
              <el-statistic title="营业收入" :value="incomeStatement.revenue" :precision="2" />
            </el-col>
            <el-col :span="8">
              <el-statistic title="营业成本" :value="incomeStatement.cost_of_goods_sold" :precision="2" />
            </el-col>
            <el-col :span="8">
              <el-statistic title="净利润" :value="incomeStatement.net_profit" :precision="2">
                <template #suffix>
                  <span :class="incomeStatement.net_profit >= 0 ? 'profit-positive' : 'profit-negative'">
                    {{ incomeStatement.net_profit >= 0 ? '盈利' : '亏损' }}
                  </span>
                </template>
              </el-statistic>
            </el-col>
          </el-row>
        </div>
      </div>
      
      <div v-else class="no-data">
        <el-empty description="暂无数据，请先录入业务数据" />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import financeApi from '../api/finance'
import { formatMoney } from '../api/common'
import { formatDate } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'

const props = defineProps({
  startDate: {
    type: String,
    default: () => new Date(new Date().getFullYear(), 0, 1).toISOString().split('T')[0]
  },
  endDate: {
    type: String,
    default: () => new Date().toISOString().split('T')[0]
  }
})

const loading = ref(false)
const incomeStatement = ref(null)
const startDate = ref(props.startDate)
const endDate = ref(props.endDate)

watch([() => props.startDate, () => props.endDate], ([newStart, newEnd]) => {
  startDate.value = newStart
  endDate.value = newEnd
  loadIncomeStatement()
})

const loadIncomeStatement = async () => {
  loading.value = true
  try {
    const response = await financeApi.getIncomeStatement(startDate.value, endDate.value)
    incomeStatement.value = response
  } catch (error) {
    ElMessage.error('加载利润表失败')
    incomeStatement.value = null
  } finally {
    loading.value = false
  }
}



const incomeData = computed(() => {
  if (!incomeStatement.value) return []
  
  const d = incomeStatement.value
  const data = []
  data.push({ item: '一、营业收入', amount: d.revenue, isTotal: true })
  data.push({ item: '  销售收入', amount: d.sale_revenue ?? 0 })
  data.push({ item: '减：营业成本', amount: d.cost_of_goods_sold, isTotal: true })
  data.push({ item: '  商品成本', amount: d.sale_cogs ?? 0 })
  data.push({ item: '  项目成本', amount: d.project_cost ?? 0 })
  data.push({ item: '二、毛利润', amount: d.gross_profit, isTotal: true })
  data.push({ item: '减：经营费用', amount: d.operating_expenses })
  data.push({ item: '三、营业利润', amount: d.operating_profit, isTotal: true })
  data.push({ item: '四、净利润', amount: d.net_profit, isTotal: true })
  
  return data
})

const exportReport = () => {
  ElMessage.info('导出功能开发中...')
}

useAccountAwareData(loadIncomeStatement)
</script>

<style scoped>
.income-statement-container {
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

.report-period {
  text-align: center;
  font-size: 16px;
  color: #666;
  margin-bottom: 30px;
}

.profit-summary {
  margin-top: 20px;
  padding: 20px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.profit-positive {
  color: #67c23a;
  font-weight: bold;
}

.profit-negative {
  color: #f56c6c;
  font-weight: bold;
}

.no-data {
  text-align: center;
  padding: 40px;
}
</style>