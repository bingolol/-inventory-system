<template>
  <div class="tax-report-container">
    <el-card shadow="never">
      <template #header>
        <span style="font-weight:600;">增值税报表</span>
      </template>
    
    <!-- 月份/季度切换 -->
    <el-radio-group v-model="reportType" @change="onReportTypeChange" style="margin-bottom: 15px;">
      <el-radio value="quarterly">按季度</el-radio>
      <el-radio value="monthly">按月份</el-radio>
    </el-radio-group>

    <!-- 季度选择 -->
    <el-form v-if="reportType === 'quarterly'" :inline="true" :model="queryForm" class="query-form">
      <el-form-item label="年份">
        <el-select v-model="queryForm.year" placeholder="请选择年份" required>
          <el-option v-for="year in years" :key="year" :label="year" :value="year" />
        </el-select>
      </el-form-item>
      <el-form-item label="季度">
        <el-select v-model="queryForm.quarter" placeholder="请选择季度" required>
          <el-option label="第一季度" value="1" />
          <el-option label="第二季度" value="2" />
          <el-option label="第三季度" value="3" />
          <el-option label="第四季度" value="4" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="getTaxReport">查询</el-button>
      </el-form-item>
    </el-form>

    <!-- 月份选择 -->
    <el-form v-else :inline="true" :model="monthlyForm" class="query-form">
      <el-form-item label="年份">
        <el-select v-model="monthlyForm.year" placeholder="请选择年份" required>
          <el-option v-for="year in years" :key="year" :label="year" :value="year" />
        </el-select>
      </el-form-item>
      <el-form-item label="月份">
        <el-select v-model="monthlyForm.month" placeholder="请选择月份" required>
          <el-option v-for="m in 12" :key="m" :label="m + '月'" :value="m" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="getMonthlyTaxReport">查询</el-button>
      </el-form-item>
    </el-form>
    </el-card>

    <!-- 纳税人身份标签 -->
    <el-tag v-if="taxReport" :type="taxReport.taxpayer_type === 'small_scale' ? 'info' : 'primary'" size="large" class="taxpayer-tag">
      {{ taxReport.taxpayer_type === 'small_scale' ? '小规模纳税人' : '一般纳税人' }}
    </el-tag>

    <!-- 报表内容 -->
    <el-card v-if="taxReport" class="report-card">
      <template #header>
        <div class="card-header">
          <span v-if="reportType === 'quarterly'">{{ queryForm.year }}年第{{ queryForm.quarter }}季度增值税报表</span>
          <span v-else>{{ monthlyForm.year }}年{{ monthlyForm.month }}月增值税报表</span>
          <span class="period">{{ taxReport.period_start }} 至 {{ taxReport.period_end }}</span>
        </div>
      </template>

      <!-- 小规模纳税人模板 -->
      <div v-if="taxReport.taxpayer_type === 'small_scale'" class="report-content">
        <el-table :data="smallScaleData" style="width: 100%">
          <el-table-column prop="item" label="项目" width="300" />
          <el-table-column prop="value" label="金额" width="200" align="right">
            <template #default="scope">
              {{ typeof scope.row.value === 'number' ? formatMoney(scope.row.value) : scope.row.value }}
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 一般纳税人模板 -->
      <div v-else class="report-content">
        <el-table :data="generalData" style="width: 100%">
          <el-table-column prop="item" label="项目" width="300" />
          <el-table-column prop="value" label="金额" width="200" align="right">
            <template #default="scope">
              {{ typeof scope.row.value === 'number' ? formatMoney(scope.row.value) : scope.row.value }}
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 发票明细 -->
      <el-collapse class="invoice-details">
        <el-collapse-item title="发票明细">
          <el-table :data="taxReport.invoice_list" style="width: 100%">
            <el-table-column prop="invoice_no" label="发票号码" width="150" />
            <el-table-column prop="direction" label="方向" width="80" align="center">
              <template #default="scope">
                <el-tag :type="scope.row.direction === 'out' ? 'primary' : 'success'">
                  {{ scope.row.direction === 'out' ? '销项' : '进项' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="invoice_type" label="类型" width="80" align="center">
              <template #default="scope">
                <el-tag :type="scope.row.invoice_type === 'special' ? 'warning' : 'info'">
                  {{ scope.row.invoice_type === 'special' ? '专票' : '普票' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="tax_rate" label="税率" width="80" align="center">
              <template #default="scope">
                {{ (Number(scope.row.tax_rate) * 100).toFixed(0) }}%
              </template>
            </el-table-column>
            <el-table-column prop="amount_without_tax" label="不含税金额" width="120" align="right">
              <template #default="scope">
                {{ formatMoney(scope.row.amount_without_tax) }}
              </template>
            </el-table-column>
            <el-table-column prop="tax_amount" label="税额" width="100" align="right">
              <template #default="scope">
                {{ formatMoney(scope.row.tax_amount) }}
              </template>
            </el-table-column>
            <el-table-column prop="counterparty_name" label="对方名称" width="150" />
            <el-table-column prop="issue_date" label="开票日期" width="120" />
          </el-table>
        </el-collapse-item>
      </el-collapse>
    </el-card>

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

// 报告类型: quarterly / monthly
const reportType = ref('quarterly')

// 季度查询表单
const queryForm = ref({
  year: new Date().getFullYear(),
  quarter: Math.floor((new Date().getMonth() + 3) / 3)
})

// 月份查询表单
const monthlyForm = ref({
  year: new Date().getFullYear(),
  month: new Date().getMonth() + 1
})

// 年份列表
const years = ref([])
// 税务报表
const taxReport = ref(null)
// 加载状态
const loading = ref(false)

// 生成年份列表
const generateYears = () => {
  const currentYear = new Date().getFullYear()
  for (let i = currentYear - 2; i <= currentYear + 2; i++) {
    years.value.push(i)
  }
}

// 小规模纳税人数据
const smallScaleData = computed(() => {
  if (!taxReport.value) return []
  return [
    { item: '一、计税依据', value: '', isHeader: true },
    { item: '  （一）应征增值税不含税销售额（3%征收率）', value: taxReport.value.total_revenue },
    { item: '二、税款计算', value: '', isHeader: true },
    { item: '  本期应纳税额', value: taxReport.value.tax_payable_gross },
    { item: '  本期应纳税额减征额', value: taxReport.value.tax_reduction },
    { item: '  应纳税额合计', value: taxReport.value.tax_payable },
    { item: '  本期预缴税额', value: taxReport.value.tax_paid },
    { item: '  本期应补（退）税额', value: taxReport.value.tax_supplement },
    { item: '三、附加税费', value: '', isHeader: true },
    { item: '  城市维护建设税本期应补（退）税额', value: taxReport.value.surcharge_stamp },
    { item: '  教育费附加本期应补（退）费额', value: taxReport.value.surcharge_education },
    { item: '  地方教育附加本期应补（退）费额', value: taxReport.value.surcharge_local_education },
    { item: '  附加税费合计', value: taxReport.value.surcharge_total },
    { item: '四、减免税明细', value: '', isHeader: true },
    { item: '  减免项目', value: taxReport.value.reduction_item },
    { item: '  减免金额', value: taxReport.value.reduction_amount }
  ]
})

// 一般纳税人数据
const generalData = computed(() => {
  if (!taxReport.value) return []
  return [
    {
      item: '销项税额',
      value: taxReport.value.output_tax
    },
    {
      item: '进项税额',
      value: taxReport.value.input_tax
    },
    {
      item: '应纳税额合计',
      value: taxReport.value.tax_payable
    }
  ]
})

// 获取季度税务报表
const getTaxReport = async () => {
  loading.value = true
  try {
    const response = await invoicesApi.getTaxReport(queryForm.value.year, queryForm.value.quarter)
    taxReport.value = response
  } catch (error) {
    console.error('获取税务报表失败:', error)
    ElMessage.error(error.response?.data?.detail || '获取税务报表失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

// 获取月度税务报表
const getMonthlyTaxReport = async () => {
  loading.value = true
  try {
    const response = await invoicesApi.getTaxReportMonthly(monthlyForm.value.year, monthlyForm.value.month)
    taxReport.value = response
  } catch (error) {
    console.error('获取月度税务报表失败:', error)
    ElMessage.error(error.response?.data?.detail || '获取月度税务报表失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

// 报告类型切换
const onReportTypeChange = () => {
  taxReport.value = null
  if (reportType.value === 'quarterly') {
    getTaxReport()
  } else {
    getMonthlyTaxReport()
  }
}

// 根据当前报告类型获取数据
const fetchData = () => {
  if (reportType.value === 'quarterly') {
    getTaxReport()
  } else {
    getMonthlyTaxReport()
  }
}

generateYears()
useAccountAwareData(fetchData)
</script>

<style scoped>
.tax-report-container {
  padding: 20px;
}

.query-form {
  margin-bottom: 20px;
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.taxpayer-tag {
  margin-bottom: 20px;
}

.report-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.period {
  font-size: 14px;
  color: #606266;
}

.report-content {
  margin: 20px 0;
}

.invoice-details {
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