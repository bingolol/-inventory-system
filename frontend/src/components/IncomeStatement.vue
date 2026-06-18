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
        <div class="report-title">利润表（会小企02表）</div>
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
            <el-col :span="6">
              <el-statistic title="营业收入" :value="incomeStatement.revenue" :precision="2" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="营业成本" :value="incomeStatement.cost_of_goods_sold" :precision="2" />
            </el-col>
            <el-col :span="6">
              <el-statistic title="营业费用" :value="incomeStatement.total_operating_expenses" :precision="2" />
            </el-col>
            <el-col :span="6">
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
  data.push({ item: '减：营业成本', amount: d.cost_of_goods_sold, isTotal: true })
  data.push({ item: '二、营业毛利', amount: d.gross_profit, isTotal: true })
  data.push({ item: '减：营业费用', amount: 0, isSubHeader: true })
  data.push({ item: '  销售费用', amount: d.selling_expenses })
  data.push({ item: '  管理费用', amount: d.administrative_expenses })
  data.push({ item: '  财务费用', amount: d.financial_expenses })
  data.push({ item: '营业费用合计', amount: d.total_operating_expenses, isTotal: true })
  data.push({ item: '三、营业利润', amount: d.operating_profit, isTotal: true })
  data.push({ item: '加：营业外收入', amount: d.non_operating_income })
  data.push({ item: '减：营业外支出', amount: d.non_operating_expense })
  data.push({ item: '四、利润总额', amount: d.gross_profit_total, isTotal: true })
  data.push({ item: '减：所得税费用', amount: d.income_tax_expense })
  data.push({ item: '五、净利润', amount: d.net_profit, isTotal: true })
  
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
  color: var(--text-regular);
  margin-bottom: 30px;
}

.profit-summary {
  margin-top: 20px;
  padding: 20px;
  background-color: var(--bg-page);
  border-radius: var(--radius);
}

.profit-positive {
  color: var(--success);
  font-weight: bold;
}

.profit-negative {
  color: var(--danger);
  font-weight: bold;
}

.no-data {
  text-align: center;
  padding: 40px;
}
</style>