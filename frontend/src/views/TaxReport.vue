<template>
  <div class="tax-report-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">税务报表</span>
          <el-button size="small" type="primary" @click="showTaxCheckDialog">税务核对</el-button>
        </div>
      </template>

      <AccountingTip page="tax" />

      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="增值税报表" name="vat">
          <VATReportSection />
        </el-tab-pane>
        <el-tab-pane label="企业所得税" name="income-tax">
          <IncomeTaxReportSection />
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="taxCheckDialogVisible" title="税务核对" width="500px">
      <el-form :model="taxCheckForm" label-width="0">
        <FormGroup title="核对参数" color="primary">
          <FormField label="期间" label-width="90px"><el-date-picker v-model="taxCheckForm.period" type="month" value-format="YYYY-MM" style="width:100%;" /></FormField>
          <FormField label="营业收入" label-width="90px"><el-input-number v-model="taxCheckForm.sales" :precision="2" style="width:100%;" controls-position="right" /></FormField>
          <FormField label="销项税" label-width="90px"><el-input-number v-model="taxCheckForm.output_vat" :precision="2" style="width:100%;" controls-position="right" /></FormField>
          <FormField label="进项税" label-width="90px"><el-input-number v-model="taxCheckForm.input_vat" :precision="2" style="width:100%;" controls-position="right" /></FormField>
          <FormField label="未交增值税" label-width="90px"><el-input-number v-model="taxCheckForm.unpaid_vat" :precision="2" style="width:100%;" controls-position="right" /></FormField>
          <FormField label="所得税" label-width="90px"><el-input-number v-model="taxCheckForm.income_tax" :precision="2" style="width:100%;" controls-position="right" /></FormField>
          <FormField label="附加税" label-width="90px"><el-input-number v-model="taxCheckForm.surcharge" :precision="2" style="width:100%;" controls-position="right" /></FormField>
          <FormField label="利润总额" label-width="90px"><el-input-number v-model="taxCheckForm.gross_profit" :precision="2" style="width:100%;" controls-position="right" /></FormField>
        </FormGroup>
      </el-form>
      <div v-if="taxCheckResult" style="margin:12px 0;">
        <FormGroup :title="taxCheckResult.all_passed ? '全部通过 ✅' : '存在差异 ❌'" :color="taxCheckResult.all_passed ? 'success' : 'danger'">
          <div v-for="(detail, key) in taxCheckResult.details" :key="key" style="font-size:12px;">
            <span :style="{ color: detail.pass ? 'var(--success)' : 'var(--danger)' }">{{ key }}: 期望={{ detail.expected }} 实际={{ detail.actual }} {{ detail.pass ? '✅' : '❌' }}</span>
          </div>
        </FormGroup>
      </div>
      <template #footer><el-button @click="taxCheckDialogVisible=false">关闭</el-button><el-button type="primary" @click="handleTaxCheck" :loading="taxChecking">核对</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import invoicesApi from '../api/invoices'
import VATReportSection from '../components/VATReportSection.vue'
import IncomeTaxReportSection from '../components/IncomeTaxReportSection.vue'
import AccountingTip from '../components/AccountingTip.vue'
import FormGroup from '../components/FormGroup.vue'
import FormField from '../components/FormField.vue'
import { handleError } from '../utils/errorHandler'
import { currentMonth } from '../utils/date'

const activeTab = ref('vat')
const taxCheckDialogVisible = ref(false)
const taxChecking = ref(false)
const taxCheckForm = ref({
  period: currentMonth(),
  sales: 0, output_vat: 0, input_vat: 0, unpaid_vat: 0,
  income_tax: 0, surcharge: 0, vat_payable: 0, gross_profit: 0
})
const taxCheckResult = ref(null)

const handleTabChange = (tab) => {
  activeTab.value = tab
}

const showTaxCheckDialog = () => {
  taxCheckResult.value = null
  taxCheckDialogVisible.value = true
}

const handleTaxCheck = async () => {
  taxChecking.value = true
  try {
    const r = await invoicesApi.taxCheck(taxCheckForm.value)
    taxCheckResult.value = r
    if (r.all_passed) {
      ElMessage.success('税务核对全部通过')
    } else {
      ElMessage.warning('税务核对存在差异，请检查明细')
    }
  } catch (e) { handleError(e, { defaultMsg: '税务核对失败' }) }
  finally { taxChecking.value = false }
}
</script>

<style scoped>
.tax-report-container { padding: 0; }
</style>
