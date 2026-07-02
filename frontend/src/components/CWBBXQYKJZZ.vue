<template>
  <div>
    <div class="cwbb-toolbar">
      <el-radio-group v-model="reportType" @change="loadData">
        <el-radio-button label="monthly">月季报</el-radio-button>
        <el-radio-button label="quarterly">季报</el-radio-button>
        <el-radio-button label="annual">年报</el-radio-button>
      </el-radio-group>
      <el-date-picker v-model="reportDate" type="date" placeholder="选择日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" @change="loadData" style="width:160px" />
      <el-button type="primary" @click="loadData" :loading="loading">查询</el-button>
      <el-button type="success" @click="exportXls" :loading="exporting" :disabled="!data">导出 .xls</el-button>
    </div>

    <div v-if="data" class="cwbb-body">
      <div class="cwbb-header">
        <div><strong>纳税人识别号：</strong>{{ data.taxpayer_id || '-' }}</div>
        <div><strong>纳税人名称：</strong>{{ data.taxpayer_name || '-' }}</div>
        <div><strong>所属期：</strong>{{ data.period_start }} 至 {{ data.period_end }}</div>
      </div>

      <el-tabs v-model="activeSheet">
        <el-tab-pane label="资产负债表（会小企01表）" name="bs">
          <el-table :data="data.balance_sheet" size="small" border class="cwbb-table">
            <el-table-column prop="line_no" label="行次" width="60" align="center" />
            <el-table-column prop="name" label="项目" />
            <el-table-column prop="end_amount" label="期末余额" align="right">
              <template #default="{ row }">{{ formatMoney(row.end_amount) }}</template>
            </el-table-column>
            <el-table-column prop="start_amount" label="年初余额" align="right">
              <template #default="{ row }">{{ formatMoney(row.start_amount) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="利润表（会小企02表）" name="is">
          <el-table :data="data.income_statement" size="small" border class="cwbb-table">
            <el-table-column prop="line_no" label="行次" width="60" align="center" />
            <el-table-column prop="name" label="项目" />
            <el-table-column v-if="reportType !== 'annual'" prop="period_amount" :label="periodLabel" align="right">
              <template #default="{ row }">{{ formatMoney(row.period_amount) }}</template>
            </el-table-column>
            <el-table-column prop="cumulative_amount" label="本年累计金额" align="right">
              <template #default="{ row }">{{ formatMoney(row.cumulative_amount) }}</template>
            </el-table-column>
            <el-table-column prop="prior_amount" :label="priorLabel" align="right">
              <template #default="{ row }">{{ formatMoney(row.prior_amount) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="现金流量表（会小企03表）" name="cf">
          <el-table :data="data.cash_flow_statement" size="small" border class="cwbb-table">
            <el-table-column prop="line_no" label="行次" width="60" align="center" />
            <el-table-column prop="name" label="项目" />
            <el-table-column v-if="reportType !== 'annual'" prop="period_amount" :label="periodLabel" align="right">
              <template #default="{ row }">{{ formatMoney(row.period_amount) }}</template>
            </el-table-column>
            <el-table-column prop="cumulative_amount" label="本年累计金额" align="right">
              <template #default="{ row }">{{ formatMoney(row.cumulative_amount) }}</template>
            </el-table-column>
            <el-table-column prop="prior_amount" :label="priorLabel" align="right">
              <template #default="{ row }">{{ formatMoney(row.prior_amount) }}</template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <div v-else style="padding:40px 0;">
      <el-empty description="暂无数据，请选择报表类型和日期后查询" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage } from 'element-plus'
import financeApi from '../api/finance'
import exportApi from '../api/export'
import { formatMoney } from '../utils/format'
import { handleError } from '../utils/errorHandler'
import { useAccountAwareData } from '../composables/useAccountAwareData'

const props = defineProps({ date: { type: String, default: () => new Date().toISOString().split('T')[0] } })

const loading = ref(false)
const exporting = ref(false)
const data = ref(null)
const reportType = ref('monthly')
const reportDate = ref(props.date)
const activeSheet = ref('bs')

const periodLabel = computed(() => reportType.value === 'monthly' ? '本期金额' : '本季度金额')
const priorLabel = computed(() => reportType.value === 'annual' ? '上年金额' : '上年同期金额')

watch(() => props.date, (v) => { reportDate.value = v; loadData() })

const loadData = async () => {
  loading.value = true
  try {
    data.value = await financeApi.getCWBBXQYKJZZ(reportType.value, reportDate.value)
  } catch (e) {
    handleError(e, { defaultMsg: '加载财务报表失败' })
    data.value = null
  } finally {
    loading.value = false
  }
}

const exportXls = async () => {
  exporting.value = true
  try {
    await exportApi.exportCWBBXQYKJZZ(reportType.value, reportDate.value)
    ElMessage.success('导出成功')
  } catch (e) {
    handleError(e, { defaultMsg: '导出失败' })
  } finally {
    exporting.value = false
  }
}

useAccountAwareData(loadData)
</script>

<style scoped>
.cwbb-toolbar { display: flex; gap: 8px; margin-bottom: 16px; align-items: center; }
.cwbb-header { display: flex; gap: 24px; margin-bottom: 16px; padding: 12px; background: var(--fill-lighter); border-radius: 4px; font-size: 13px; color: var(--text-regular); }
.cwbb-header strong { color: var(--text-primary); }
.cwbb-body { animation: cwbb-in 0.3s ease; }
@keyframes cwbb-in { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }
.cwbb-table { width: 100%; }
</style>
