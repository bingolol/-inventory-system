<template>
  <div class="income-tax-report-container" v-loading="loading">
    <el-card shadow="never">
      <template #header>
        <span class="page-title">企业所得税报表（税务口径）</span>
      </template>

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
    </el-card>

    <!-- 报表内容 -->
    <el-card v-if="incomeTaxReport" shadow="never">
      <template #header>
        <span>{{ queryForm.year }}年第{{ queryForm.quarter }}季度企业所得税报表</span>
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
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
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
    { item: '一、营业收入', value: r.operating_revenue },
    { item: '二、营业成本', value: r.operating_cost },
    { item: '三、利润总额', value: r.gross_profit },
    { item: '四、加：特定业务计算的应纳税所得额', value: r.special_business_income },
    { item: '五、减：免税收入、减计收入、加计扣除', value: '', isHeader: true },
    { item: '  免税收入', value: r.tax_exempt_income },
    { item: '  减计收入', value: r.tax_deduction_income },
    { item: '  加计扣除', value: r.additional_deduction },
    { item: '六、减：减免所得额', value: r.tax_reduction_income },
    { item: '七、实际利润额', value: r.actual_profit },
    { item: '八、税率', value: `${(r.tax_rate * 100).toFixed(0)}%` },
    { item: '九、应纳所得税额', value: r.tax_payable },
    { item: '十、减：减免所得税额', value: '', isHeader: true },
    { item: '  小微企业减免', value: r.small_micro_discount },
    { item: '十一、实际应纳所得税额', value: r.actual_tax_payable },
    { item: '十二、加：特定业务预缴所得税额', value: r.special_business_prepaid },
    { item: '十三、减：已预缴所得税额', value: r.prepaid_tax },
    { item: '十四、本期应补(退)所得税额', value: r.tax_supplement }
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

.report-content {
  margin: 20px 0;
}
</style>
