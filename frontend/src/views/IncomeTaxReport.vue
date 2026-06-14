<template>
  <div class="income-tax-report-container">
    <el-card shadow="never">
      <template #header>
        <span style="font-weight:600;">企业所得税报表（税务口径）</span>
      </template>
    
    <!-- 年份/季度选择 -->
    <el-form :inline="true" :model="queryForm" class="query-form">
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
    </el-card>

    <!-- 报表内容 -->
    <el-card v-if="incomeTaxReport" class="report-card">
      <template #header>
        <div class="card-header">
          <span>{{ queryForm.year }}年第{{ queryForm.quarter }}季度企业所得税报表</span>
        </div>
      </template>

      <div class="report-content">
        <el-table :data="reportData" style="width: 100%">
          <el-table-column prop="item" label="项目" width="300" />
          <el-table-column prop="value" label="金额" width="200" align="right">
            <template #default="scope">
              {{ typeof scope.row.value === 'number' ? formatMoney(scope.row.value) : scope.row.value }}
            </template>
          </el-table-column>
        </el-table>
      </div>

    </el-card>

    <el-empty v-else-if="!loading" description="请选择年份和季度后点击查询" />

    <!-- 加载中 -->
    <div v-if="loading" class="loading-overlay">
      <el-icon class="loading-icon"><Loading /></el-icon>
      <span>加载中...</span>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Loading } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAccountStore } from '../stores/account'
const accountStore = useAccountStore()
import invoicesApi from '../api/invoices'
import { formatMoney } from '../api/common'
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

// 报表数据
const reportData = computed(() => {
  if (!incomeTaxReport.value) return []
  const r = incomeTaxReport.value
  return [
    {
      item: '一、营业收入（销项发票不含税）',
      value: r.total_revenue
    },
    {
      item: '  销项发票收入',
      value: r.invoice_revenue ?? r.total_revenue
    },
    {
      item: '减：营业成本（进项发票不含税）',
      value: r.total_cost
    },
    {
      item: '  进项发票成本',
      value: r.invoice_cost ?? r.total_cost
    },
    {
      item: '等于：毛利润',
      value: r.gross_profit
    },
    {
      item: '减：有票费用（可税前扣除）',
      value: r.operating_expenses
    },
    {
      item: '  有票费用',
      value: r.invoiced_expenses ?? r.operating_expenses
    },
    {
      item: '  无票费用（不可扣除，仅供参考）',
      value: r.non_invoice_expenses ?? 0
    },
    {
      item: '等于：应纳税所得额',
      value: r.taxable_income
    },
    {
      item: '乘以：税率',
      value: `${(r.tax_rate * 100).toFixed(0)}%`
    },
    {
      item: '等于：应纳企业所得税',
      value: r.tax_amount
    }
  ]
})

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
