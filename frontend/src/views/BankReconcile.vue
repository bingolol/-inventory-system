<template>
  <div v-loading="loading">
    <StatCards :items="[
      { label: '对账期间', value: period, color: 'primary' },
      { label: '调节表状态', value: reconciliation?.status || '-', color: statusColor },
      { label: '是否平衡', value: reconciliation?.balanced === true ? '平衡 ✅' : reconciliation?.balanced === false ? '不平衡 ❌' : '-', color: reconciliation?.balanced === true ? 'success' : reconciliation?.balanced === false ? 'danger' : 'text-placeholder' }
    ]" />

    <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px;">
      <el-date-picker v-model="period" type="month" value-format="YYYY-MM" style="width:160px;" placeholder="选择月份" @change="loadReconciliation" />
      <el-button type="primary" @click="showImportDialog">导入对账单</el-button>
      <el-button @click="handleReconcile" :disabled="!statementImported">执行对账</el-button>
      <el-button @click="handleGenerateEntry" :disabled="!reconciliation?.id">生成补录凭证</el-button>
      <el-button type="success" @click="handleConfirm" :disabled="!reconciliation?.id || reconciliation?.status==='confirmed'">确认调节表</el-button>
      <el-button size="small" @click="showBankEntryDialog">银行手续费/利息</el-button>
    </div>

    <div v-if="reconciliation?.id" class="box" style="margin-bottom:16px;">
      <div class="bh"><span class="bt">调节表摘要</span></div>
      <table class="tbl">
        <tr><th>项目</th><th>金额</th></tr>
        <tr><td>银行对账单余额</td><td style="font-weight:600;">¥{{ formatMoney(reconciliation.statement_balance) }}</td></tr>
        <tr><td>公司账面余额</td><td style="font-weight:600;">¥{{ formatMoney(reconciliation.book_balance) }}</td></tr>
        <tr><td>调整后银行余额</td><td>¥{{ formatMoney(reconciliation.adjusted_statement) }}</td></tr>
        <tr><td>调整后账面余额</td><td>¥{{ formatMoney(reconciliation.adjusted_book) }}</td></tr>
      </table>
    </div>

    <div v-if="reconciliation?.items?.length" class="box">
      <div class="bh"><span class="bt">调节项目 ({{ reconciliation.items.length }})</span></div>
      <table class="tbl">
        <tr><th>类型</th><th>金额</th><th>方向</th><th>状态</th><th>备注</th></tr>
        <tr v-for="item in reconciliation.items" :key="item.id">
          <td>{{ item.item_type }}</td>
          <td style="font-weight:600;">¥{{ formatMoney(item.amount) }}</td>
          <td><span class="bg" :class="item.direction==='in'?'bs':'bd'">{{ item.direction==='in'?'加':'减' }}</span></td>
          <td><StatusTag :status="item.resolved?'resolved':'pending'" :color="item.resolved?'success':'warning'" :label="item.resolved?'已处理':'待处理'" /></td>
          <td style="color:var(--text-secondary);">{{ item.notes||'-' }}</td>
        </tr>
      </table>
    </div>

    <el-dialog v-model="importDialogVisible" title="导入银行对账单" width="520px">
      <el-form :model="stmtForm" label-width="0">
        <FormGroup title="对账单信息" color="primary">
          <FormField label="开始日期" label-width="80px"><el-date-picker v-model="stmtForm.period_start" type="date" value-format="YYYY-MM-DD" style="width:100%;" /></FormField>
          <FormField label="结束日期" label-width="80px"><el-date-picker v-model="stmtForm.period_end" type="date" value-format="YYYY-MM-DD" style="width:100%;" /></FormField>
          <FormField label="期初余额" label-width="80px"><el-input-number v-model="stmtForm.opening_balance" :precision="2" style="width:100%;" controls-position="right" /></FormField>
          <FormField label="期末余额" label-width="80px"><el-input-number v-model="stmtForm.closing_balance" :precision="2" style="width:100%;" controls-position="right" /></FormField>
        </FormGroup>
        <FormGroup title="对账单明细" color="success" style="margin-top:12px;">
          <div v-for="(line, idx) in stmtForm.lines" :key="line._key" style="display:flex;gap:8px;align-items:center;margin-bottom:6px;">
            <el-date-picker v-model="line.transaction_date" type="date" value-format="YYYY-MM-DD" style="width:130px;" />
            <el-input-number v-model="line.amount" :precision="2" style="width:130px;" controls-position="right" />
            <el-input v-model="line.description" placeholder="描述" style="flex:1;" />
            <el-button size="small" type="danger" link @click="stmtForm.lines.splice(idx, 1)">×</el-button>
          </div>
          <el-button size="small" @click="stmtForm.lines.push({_key: newLineKey(), transaction_date:'',amount:0,description:''})">+ 添加一行</el-button>
        </FormGroup>
      </el-form>
      <template #footer><el-button @click="importDialogVisible=false">取消</el-button><el-button type="primary" @click="handleImport" :loading="importing">导入</el-button></template>
    </el-dialog>

    <el-dialog v-model="bankEntryDialogVisible" title="银行手续费/利息直录" width="460px">
      <el-form :model="bankEntryForm" label-width="0">
        <FormGroup title="录入信息" color="warning">
          <FormField label="类型" label-width="80px"><el-select v-model="bankEntryForm.entry_type" style="width:100%"><el-option label="利息收入" value="interest_income" /><el-option label="银行手续费" value="bank_fee" /></el-select></FormField>
          <FormField label="金额" label-width="80px"><el-input-number v-model="bankEntryForm.amount" :precision="2" style="width:100%;" controls-position="right" /></FormField>
          <FormField label="日期" label-width="80px"><el-date-picker v-model="bankEntryForm.transaction_date" type="date" value-format="YYYY-MM-DD" style="width:100%;" /></FormField>
          <FormField label="描述" label-width="80px"><el-input v-model="bankEntryForm.description" /></FormField>
        </FormGroup>
      </el-form>
      <template #footer><el-button @click="bankEntryDialogVisible=false">取消</el-button><el-button type="primary" @click="handleBankEntry" :loading="bankEntering">录入</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import StatCards from '../components/StatCards.vue'
import FormGroup from '../components/FormGroup.vue'
import FormField from '../components/FormField.vue'
import StatusTag from '../components/StatusTag.vue'
import bankReconcileApi from '../api/bankReconcile'
import { formatMoney } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../utils/errorHandler'
import { currentMonth, today, periodRange } from '../utils/date'

let lineKey = 0
function newLineKey() { return ++lineKey }

const loading = ref(false)
const period = ref(currentMonth())
const reconciliation = ref(null)
const statementImported = ref(false)
const importDialogVisible = ref(false)
const importing = ref(false)
const bankEntryDialogVisible = ref(false)
const bankEntering = ref(false)

const stmtForm = ref({
  period_start: '', period_end: '',
  opening_balance: 0, closing_balance: 0,
  lines: []
})

const bankEntryForm = ref({
  entry_type: 'bank_fee', amount: 0, transaction_date: today(), description: ''
})

const statusColor = computed(() => {
  const s = reconciliation.value?.status
  if (!s) return 'text-placeholder'
  if (s === 'confirmed') return 'success'
  if (s === 'pending') return 'warning'
  return 'primary'
})

const loadReconciliation = async () => {
  if (!period.value) return
  loading.value = true
  try {
    const r = await bankReconcileApi.getReconciliation(period.value)
    if (r.exists === false) {
      reconciliation.value = { status: null, balanced: null }
      statementImported.value = false
    } else {
      reconciliation.value = r
      statementImported.value = true
    }
  } catch (e) {
    reconciliation.value = { status: null, balanced: null }
    statementImported.value = false
    if (e?.response?.data?.error?.code !== 'BANK_ACCOUNT_NOT_FOUND') {
      handleError(e, { defaultMsg: '获取对账结果失败' })
    }
  } finally { loading.value = false }
}

const showImportDialog = () => {
  const { start, end } = periodRange(period.value)
  stmtForm.value = {
    period_start: start,
    period_end: end,
    opening_balance: 0, closing_balance: 0,
    lines: []
  }
  importDialogVisible.value = true
}

const handleImport = async () => {
  importing.value = true
  try {
    await bankReconcileApi.importBankStatement(stmtForm.value)
    ElMessage.success('对账单导入成功')
    importDialogVisible.value = false
    statementImported.value = true
  } catch (e) { handleError(e, { defaultMsg: '导入对账单失败' }) }
  finally { importing.value = false }
}

const handleReconcile = async () => {
  loading.value = true
  try {
    await bankReconcileApi.reconcileBank(period.value)
    ElMessage.success('对账完成')
    await loadReconciliation()
  } catch (e) { handleError(e, { defaultMsg: '执行对账失败' }) }
  finally { loading.value = false }
}

const handleGenerateEntry = async () => {
  if (!reconciliation.value?.id) return
  try {
    await bankReconcileApi.generateReconciliationEntry(reconciliation.value.id)
    ElMessage.success('补录凭证已生成')
    await loadReconciliation()
  } catch (e) { handleError(e, { defaultMsg: '生成补录凭证失败' }) }
}

const handleConfirm = async () => {
  if (!reconciliation.value?.id) return
  if (reconciliation.value.status === 'confirmed') { ElMessage.warning('调节表已确认'); return }
  try {
    await bankReconcileApi.confirmReconciliation(reconciliation.value.id)
    ElMessage.success('调节表已确认')
    await loadReconciliation()
  } catch (e) { handleError(e, { defaultMsg: '确认调节表失败' }) }
}

const showBankEntryDialog = () => {
  bankEntryForm.value = {
    entry_type: 'bank_fee', amount: 0,
    transaction_date: today(), description: ''
  }
  bankEntryDialogVisible.value = true
}

const handleBankEntry = async () => {
  bankEntering.value = true
  try {
    await bankReconcileApi.createBankEntry(bankEntryForm.value)
    ElMessage.success('录入成功')
    bankEntryDialogVisible.value = false
    await loadReconciliation()
  } catch (e) { handleError(e, { defaultMsg: '录入失败' }) }
  finally { bankEntering.value = false }
}

useAccountAwareData(loadReconciliation)
</script>

<style scoped>
.box { background:var(--bg-card); border:1px solid var(--border-lighter); border-radius:10px; padding:16px; }
.bh { display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }
.bt { font-size:13px; font-weight:600; color:var(--text-primary); }
.tbl { width:100%; border-collapse:collapse; }
.tbl th { text-align:left; padding:8px 10px; font-size:11px; font-weight:600; color:var(--text-secondary); border-bottom:1px solid var(--border-lighter); }
.tbl td { padding:8px 10px; font-size:13px; color:var(--text-regular); border-bottom:1px solid var(--bg-elevated); }
.tbl tr:last-child td { border:none; }
.bg { display:inline-block; padding:1px 8px; border-radius:4px; font-size:11px; font-weight:500; }
.bs { background:var(--success-light); color:var(--success); }
.bd { background:var(--danger-light); color:var(--danger); }
</style>
