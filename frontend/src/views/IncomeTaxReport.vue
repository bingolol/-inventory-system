<template>
  <div class="income-tax-report-container">
    <h2>企业所得税报表</h2>
    
    <!-- 年份选择 -->
    <el-form :inline="true" :model="queryForm" class="query-form">
      <el-form-item label="年份">
        <el-select v-model="queryForm.year" placeholder="请选择年份" required>
          <el-option v-for="year in years" :key="year" :label="year" :value="year" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="getIncomeTaxReport">查询</el-button>
      </el-form-item>
    </el-form>

    <!-- 报表内容 -->
    <el-card v-if="incomeTaxReport" class="report-card">
      <template #header>
        <div class="card-header">
          <span>{{ queryForm.year }}年度企业所得税报表</span>
        </div>
      </template>

      <div class="report-content">
        <el-table :data="reportData" style="width: 100%">
          <el-table-column prop="item" label="项目" width="300" />
          <el-table-column prop="value" label="金额" width="200" align="right">
            <template #default="scope">
              {{ typeof scope.row.value === 'number' ? scope.row.value.toFixed(2) : scope.row.value }}
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 注：明细数据需从后端 API 获取，当前仅显示汇总数据 -->
    </el-card>

    <!-- 加载中 -->
    <div v-if="loading" class="loading-overlay">
      <el-icon class="loading-icon"><Loading /></el-icon>
      <span>加载中...</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { accountStore } from '../stores/account'
import api from '../api'

// 查询表单
const queryForm = ref({
  year: new Date().getFullYear() - 1 // 默认查询上一年
})

// 年份列表
const years = ref([])
// 企业所得税报表
const incomeTaxReport = ref(null)
// 加载状态
const loading = ref(false)

// 未使用的数据引用 - 预留用于未来明细功能
const incomeDetails = ref([])
// 未使用的成本明细 - 预留用于未来明细功能
const costDetails = ref([])
// 未使用的费用明细 - 预留用于未来明细功能
const expenseDetails = ref([])

// 生成年份列表
const generateYears = () => {
  const currentYear = new Date().getFullYear()
  for (let i = currentYear - 3; i <= currentYear; i++) {
    years.value.push(i)
  }
}

// 报表数据
const reportData = computed(() => {
  if (!incomeTaxReport.value) return []
  return [
    {
      item: '全年营业收入',
      value: incomeTaxReport.value.total_revenue
    },
    {
      item: '减：营业成本',
      value: incomeTaxReport.value.total_cost
    },
    {
      item: '等于：毛利润',
      value: incomeTaxReport.value.gross_profit
    },
    {
      item: '减：经营费用',
      value: incomeTaxReport.value.operating_expenses
    },
    {
      item: '等于：应纳税所得额',
      value: incomeTaxReport.value.taxable_income
    },
    {
      item: '乘以：税率',
      value: `${(incomeTaxReport.value.tax_rate * 100).toFixed(0)}%`
    },
    {
      item: '等于：应纳企业所得税',
      value: incomeTaxReport.value.tax_amount
    }
  ]
})

// 获取企业所得税报表
const getIncomeTaxReport = async () => {
  loading.value = true
  try {
    const response = await api.getIncomeTaxReport(queryForm.value.year)
    incomeTaxReport.value = response
    
    // TODO: 后续补充明细 API
  } catch (error) {
    console.error('获取企业所得税报表失败:', error)
  } finally {
    loading.value = false
  }
}

// 明细数据功能占位（从后端API获取）
const loadDetails = () => {
  // 模拟收入明细
  incomeDetails.value = [
    { date: `${queryForm.value.year}-01-15`, customer: '客户A', amount: 50000, notes: '销售商品' },
    { date: `${queryForm.value.year}-03-20`, customer: '客户B', amount: 80000, notes: '提供服务' },
    { date: `${queryForm.value.year}-06-10`, customer: '客户C', amount: 60000, notes: '销售商品' },
    { date: `${queryForm.value.year}-09-05`, customer: '客户A', amount: 70000, notes: '提供服务' },
    { date: `${queryForm.value.year}-12-20`, customer: '客户D', amount: 90000, notes: '销售商品' }
  ]
  
  // 模拟成本明细
  costDetails.value = [
    { date: `${queryForm.value.year}-01-10`, supplier: '供应商A', amount: 20000, notes: '采购原材料' },
    { date: `${queryForm.value.year}-03-15`, supplier: '供应商B', amount: 30000, notes: '采购设备' },
    { date: `${queryForm.value.year}-06-05`, supplier: '供应商C', amount: 25000, notes: '采购原材料' },
    { date: `${queryForm.value.year}-09-10`, supplier: '供应商A', amount: 35000, notes: '采购原材料' },
    { date: `${queryForm.value.year}-12-15`, supplier: '供应商D', amount: 40000, notes: '采购设备' }
  ]
  
  // 模拟费用明细
  expenseDetails.value = [
    { date: `${queryForm.value.year}-01-05`, category: '房租', amount: 5000, description: '办公室租金' },
    { date: `${queryForm.value.year}-02-01`, category: '水电', amount: 1500, description: '水电费' },
    { date: `${queryForm.value.year}-03-10`, category: '工资', amount: 15000, description: '员工工资' },
    { date: `${queryForm.value.year}-04-05`, category: '其他', amount: 2000, description: '办公用品' },
    { date: `${queryForm.value.year}-05-15`, category: '房租', amount: 5000, description: '办公室租金' },
    { date: `${queryForm.value.year}-06-01`, category: '水电', amount: 1600, description: '水电费' },
    { date: `${queryForm.value.year}-07-10`, category: '工资', amount: 15000, description: '员工工资' },
    { date: `${queryForm.value.year}-08-05`, category: '其他', amount: 1800, description: '办公用品' },
    { date: `${queryForm.value.year}-09-15`, category: '房租', amount: 5000, description: '办公室租金' },
    { date: `${queryForm.value.year}-10-01`, category: '水电', amount: 1700, description: '水电费' },
    { date: `${queryForm.value.year}-11-10`, category: '工资', amount: 15000, description: '员工工资' },
    { date: `${queryForm.value.year}-12-05`, category: '其他', amount: 2200, description: '办公用品' }
  ]
}

onMounted(() => {
  generateYears()
  getIncomeTaxReport()
})
</script>

<style scoped>
.income-tax-report-container {
  padding: 20px;
}

.query-form {
  margin-bottom: 20px;
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.report-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.report-content {
  margin: 20px 0;
}

.details {
  margin-top: 20px;
}

.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.loading-icon {
  font-size: 48px;
  color: #fff;
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
