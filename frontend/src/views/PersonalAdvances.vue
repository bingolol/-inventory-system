<template>
  <div>
    <StatCards :items="[
      { label: '总垫付', value: formatMoney(totals.total_amount), color: 'primary' },
      { label: '已偿还', value: formatMoney(totals.paid_amount), color: 'success' },
      { label: '未还余额', value: formatMoney(totals.remaining_amount), color: 'danger' }
    ]" />

    <el-card shadow="never">
      <template #header>
        <PageHeader title="个人垫付管理">
          <template #actions>
            <el-button type="primary" @click="openCreateDialog">
              <el-icon><Plus /></el-icon> 新增垫付
            </el-button>
          </template>
        </PageHeader>
      </template>
      <div class="filter-bar" style="margin-bottom:12px;">
        <el-input v-model="filterForm.advancer_name" placeholder="垫付人姓名" clearable style="width:160px;" />
        <el-select v-model="filterForm.status" placeholder="状态" clearable style="width:120px;">
          <el-option label="未偿还" value="unpaid" />
          <el-option label="部分偿还" value="partial" />
          <el-option label="已还清" value="paid" />
        </el-select>
        <el-date-picker v-model="filterForm.start_date" type="date" value-format="YYYY-MM-DD" placeholder="开始日期" style="width:150px;" />
        <el-date-picker v-model="filterForm.end_date" type="date" value-format="YYYY-MM-DD" placeholder="结束日期" style="width:150px;" />
        <el-button type="primary" @click="loadList">查询</el-button>
        <el-button @click="resetFilter">重置</el-button>
      </div>
      <el-table :data="advances" stripe style="width:100%" v-loading="loading">
        <template #empty>
          <el-empty description="暂无垫付记录" />
        </template>
        <el-table-column prop="advance_no" label="单号" min-width="140">
          <template #default="{ row }">
            <span :class="{ 'reversed-tag': row.is_reversed }">{{ row.advance_no }}</span>
            <el-tag v-if="row.is_reversed" size="small" type="info" style="margin-left:6px;">已冲红</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="advancer_name" label="垫付人" min-width="100" />
        <el-table-column label="日期" min-width="110">
          <template #default="{ row }">{{ formatDate(row.advance_date) }}</template>
        </el-table-column>
        <el-table-column label="金额" min-width="120" align="right">
          <template #default="{ row }"><span class="money">{{ formatMoney(row.amount) }}</span></template>
        </el-table-column>
        <el-table-column label="借方科目" min-width="100">
          <template #default="{ row }">{{ debitAccountLabel(row.debit_account_code) }}</template>
        </el-table-column>
        <el-table-column label="已还/未还" min-width="160" align="right">
          <template #default="{ row }">
            <div>{{ formatMoney(row.paid_amount) }} / <span :style="{ color: row.remaining_amount > 0 ? 'var(--danger)' : 'var(--success)' }">{{ formatMoney(row.remaining_amount) }}</span></div>
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.repayment_status)" size="small">{{ statusLabel(row.repayment_status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="说明" min-width="180">
          <template #default="{ row }">{{ row.description || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="240" align="center" fixed="right">
          <template #default="{ row }">
            <ActionColumn :actions="[
              { key: 'repay', label: '偿还', disabled: row.is_reversed || row.remaining_amount <= 0 },
              { key: 'repayments', label: '偿还记录', type: 'info' },
              { key: 'reverse', label: '冲红', type: 'danger', confirm: '确定冲红此垫付单？（须先冲红所有偿还记录）', disabled: row.is_reversed }
            ]" @click="(key) => {
              if (key === 'repay') openRepayDialog(row)
              else if (key === 'repayments') viewRepayments(row)
              else if (key === 'reverse') handleReverseAdvance(row)
            }" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 创建垫付对话框 -->
    <el-dialog v-model="createDialogVisible" title="新增个人垫付" width="540px">
      <el-form :model="createForm" label-width="0">
        <FormGroup title="垫付信息" color="primary">
          <FormField label="垫付人" label-width="90px"><el-input v-model="createForm.advancer_name" placeholder="如 老板张三" /></FormField>
          <FormField label="金额" label-width="90px"><el-input v-model.number="createForm.amount" type="number" /></FormField>
          <FormField label="垫付日期" label-width="90px"><el-date-picker v-model="createForm.advance_date" type="date" value-format="YYYY-MM-DD" style="width:100%;" /></FormField>
          <FormField label="用途（借方科目）" label-width="90px">
            <el-select v-model="createForm.debit_account_code" style="width:100%;">
              <el-option v-for="o in debitAccountOptions" :key="o.value" :label="o.label" :value="o.value" />
            </el-select>
          </FormField>
          <FormField label="说明" label-width="90px"><el-input v-model="createForm.description" type="textarea" :rows="2" placeholder="用途说明（可选）" /></FormField>
        </FormGroup>
      </el-form>
      <template #footer>
        <el-button @click="createDialogVisible=false">取消</el-button>
        <el-button type="primary" @click="saveCreate">保存</el-button>
      </template>
    </el-dialog>

    <!-- 偿还对话框 -->
    <el-dialog v-model="repayDialogVisible" :title="`偿还垫付单 ${repayTarget?.advance_no || ''}`" width="500px">
      <el-form :model="repayForm" label-width="0">
        <FormGroup title="偿还信息" color="success">
          <div class="info-line">垫付人: <b>{{ repayTarget?.advancer_name }}</b></div>
          <div class="info-line">总额: {{ formatMoney(repayTarget?.amount) }}　已还: {{ formatMoney(repayTarget?.paid_amount) }}　未还: <span style="color:var(--danger);">{{ formatMoney(repayTarget?.remaining_amount) }}</span></div>
          <FormField label="偿还金额" label-width="90px"><el-input v-model.number="repayForm.amount" type="number" /></FormField>
          <FormField label="偿还日期" label-width="90px"><el-date-picker v-model="repayForm.repayment_date" type="date" value-format="YYYY-MM-DD" style="width:100%;" /></FormField>
          <FormField label="支付方式" label-width="90px">
            <el-select v-model="repayForm.bank_account_id" placeholder="选择银行账户（留空=现金）" clearable style="width:100%;">
              <el-option v-for="b in bankAccounts" :key="b.id" :label="`${b.bank_name} (${formatMoney(b.balance)})`" :value="b.id" />
            </el-select>
          </FormField>
          <FormField label="说明" label-width="90px"><el-input v-model="repayForm.description" type="textarea" :rows="2" /></FormField>
        </FormGroup>
      </el-form>
      <template #footer>
        <el-button @click="repayDialogVisible=false">取消</el-button>
        <el-button type="primary" @click="saveRepay">确认偿还</el-button>
      </template>
    </el-dialog>

    <!-- 偿还记录抽屉 -->
    <el-drawer v-model="repaymentsDrawerVisible" :title="`偿还记录 - ${repayTarget?.advance_no || ''}`" size="600px" direction="rtl">
      <el-table :data="repayments" stripe v-loading="repaymentsLoading">
        <template #empty><el-empty description="暂无偿还记录" /></template>
        <el-table-column label="日期" min-width="110">
          <template #default="{ row }">{{ formatDate(row.repayment_date) }}</template>
        </el-table-column>
        <el-table-column label="金额" min-width="100" align="right">
          <template #default="{ row }"><span style="color:var(--success);">{{ formatMoney(row.amount) }}</span></template>
        </el-table-column>
        <el-table-column label="支付方式" min-width="120">
          <template #default="{ row }">{{ row.bank_account_id ? '银行' : '现金' }}</template>
        </el-table-column>
        <el-table-column prop="description" label="说明" min-width="160">
          <template #default="{ row }">{{ row.description || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <ActionColumn :actions="[{ key: 'reverse', label: '冲红', type: 'danger', confirm: '确定冲红此偿还记录？', disabled: row.is_reversed }]" @click="(key) => { if (key === 'reverse') handleReverseRepayment(row) }" />
          </template>
        </el-table-column>
      </el-table>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import StatCards from '../components/StatCards.vue'
import PageHeader from '../components/PageHeader.vue'
import FormGroup from '../components/FormGroup.vue'
import FormField from '../components/FormField.vue'
import ActionColumn from '../components/ActionColumn.vue'
import advancesApi from '../api/personalAdvances'
import bankAccountsApi from '../api/bankAccounts'
import { formatMoney, formatDate } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../utils/errorHandler'
import { today } from '../utils/date'

const advances = ref([])
const loading = ref(false)
const totals = ref({ total_amount: 0, paid_amount: 0, remaining_amount: 0 })
const filterForm = ref({ advancer_name: '', status: '', start_date: '', end_date: '' })

// 借方科目选项（与后端 PERSONAL_ADVANCE_DEBIT_ACCOUNTS 一致）
const debitAccountOptions = [
  { value: '6601', label: '6601 管理费用（默认）' },
  { value: '6602', label: '6602 销售费用' },
  { value: '1405', label: '1405 库存商品' },
  { value: '1601', label: '1601 固定资产' },
  { value: '1701', label: '1701 无形资产' },
]
const debitAccountLabel = (code) => {
  const o = debitAccountOptions.find(o => o.value === code)
  return o ? o.label.split(' ')[1] : code
}
const statusLabel = (s) => ({ unpaid: '未偿还', partial: '部分偿还', paid: '已还清' }[s] || s)
const statusTagType = (s) => ({ unpaid: 'danger', partial: 'warning', paid: 'success' }[s] || 'info')

// 创建垫付
const createDialogVisible = ref(false)
const createForm = ref({ advancer_name: '', amount: 0, advance_date: '', debit_account_code: '6601', description: '' })

// 偿还
const repayDialogVisible = ref(false)
const repayTarget = ref(null)
const repayForm = ref({ amount: 0, repayment_date: '', bank_account_id: null, description: '' })
const bankAccounts = ref([])

// 偿还记录抽屉
const repaymentsDrawerVisible = ref(false)
const repayments = ref([])
const repaymentsLoading = ref(false)

const loadList = async () => {
  loading.value = true
  try {
    const params = {}
    if (filterForm.value.advancer_name) params.advancer_name = filterForm.value.advancer_name
    if (filterForm.value.status) params.status = filterForm.value.status
    if (filterForm.value.start_date) params.start_date = filterForm.value.start_date
    if (filterForm.value.end_date) params.end_date = filterForm.value.end_date
    const r = await advancesApi.getPersonalAdvances(params)
    advances.value = r?.items || []
    await loadTotals()
  } catch (e) { handleError(e, { defaultMsg: '获取垫付列表失败' }); advances.value = [] }
  finally { loading.value = false }
}

const loadTotals = async () => {
  try {
    totals.value = await advancesApi.getPersonalAdvanceTotals() || { total_amount: 0, paid_amount: 0, remaining_amount: 0 }
  } catch (e) { /* 静默 */ }
}

const resetFilter = () => { filterForm.value = { advancer_name: '', status: '', start_date: '', end_date: '' }; loadList() }

const openCreateDialog = () => {
  createForm.value = {
    advancer_name: '',
    amount: 0,
    advance_date: today(),
    debit_account_code: '6601',
    description: '',
  }
  createDialogVisible.value = true
}

const saveCreate = async () => {
  if (!createForm.value.advancer_name?.trim()) { ElMessage.warning('请填写垫付人'); return }
  if (!createForm.value.amount || createForm.value.amount <= 0) { ElMessage.warning('金额必须大于 0'); return }
  if (!createForm.value.advance_date) { ElMessage.warning('请选择垫付日期'); return }
  try {
    await advancesApi.createPersonalAdvance(createForm.value)
    ElMessage.success('垫付单已创建')
    createDialogVisible.value = false
    loadList()
  } catch (e) { handleError(e, { defaultMsg: '创建失败' }) }
}

const openRepayDialog = async (row) => {
  repayTarget.value = row
  repayForm.value = {
    amount: row.remaining_amount,
    repayment_date: today(),
    bank_account_id: null,
    description: '',
  }
  // 加载银行账户列表
  try {
    const r = await bankAccountsApi.getBankAccounts()
    bankAccounts.value = r?.items || r || []
  } catch (e) { bankAccounts.value = [] }
  repayDialogVisible.value = true
}

const saveRepay = async () => {
  if (!repayTarget.value) { ElMessage.warning('请先选择垫付单'); return }
  if (!repayForm.value.amount || repayForm.value.amount <= 0) { ElMessage.warning('偿还金额必须大于 0'); return }
  if (!repayForm.value.repayment_date) { ElMessage.warning('请选择偿还日期'); return }
  if (repayForm.value.amount > repayTarget.value.remaining_amount) {
    ElMessage.warning(`偿还金额超过未还余额 ${repayTarget.value.remaining_amount}`)
    return
  }
  try {
    await advancesApi.repayPersonalAdvance(repayTarget.value.id, repayForm.value)
    ElMessage.success('偿还成功')
    repayDialogVisible.value = false
    loadList()
  } catch (e) { handleError(e, { defaultMsg: '偿还失败' }) }
}

const viewRepayments = async (row) => {
  repayTarget.value = row
  repaymentsDrawerVisible.value = true
  repaymentsLoading.value = true
  try {
    repayments.value = await advancesApi.listPersonalAdvanceRepayments(row.id) || []
  } catch (e) { handleError(e, { defaultMsg: '获取偿还记录失败' }); repayments.value = [] }
  finally { repaymentsLoading.value = false }
}

const handleReverseAdvance = async (row) => {
  try {
    await advancesApi.reversePersonalAdvance(row.id)
    ElMessage.success('垫付单已冲红')
    loadList()
  } catch (e) { handleError(e, { defaultMsg: '冲红失败' }) }
}

const handleReverseRepayment = async (row) => {
  if (!repayTarget.value) { ElMessage.warning('请先选择垫付单'); return }
  try {
    await advancesApi.reversePersonalAdvanceRepayment(repayTarget.value.id, row.id)
    ElMessage.success('偿还记录已冲红')
    // 刷新偿还记录 + 列表
    viewRepayments(repayTarget.value)
    loadList()
  } catch (e) { handleError(e, { defaultMsg: '冲红失败' }) }
}

useAccountAwareData(loadList)
</script>

<style scoped>
.info-line { font-size:13px; color:var(--text-regular); margin-bottom:4px; }
.reversed-tag { color: var(--text-secondary); text-decoration: line-through; }
.money { font-variant-numeric: tabular-nums; }
</style>
