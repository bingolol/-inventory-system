<template>
  <div v-loading="loading">
    <div class="ba-header">
      <div class="ba-header-left">
        <el-select v-model="currentAccountId" placeholder="选择银行账户" style="width:280px" @change="onAccountChange">
          <el-option v-for="acc in accounts" :key="acc.id" :label="acc.bank_name + ' (****' + acc.account_number.slice(-4) + ')'" :value="acc.id">
            <div class="ba-opt">
              <span>{{ acc.bank_name }}</span>
              <span class="ba-opt-balance">{{ formatMoney(acc.balance) }}</span>
            </div>
          </el-option>
        </el-select>
      </div>
      <div class="ba-header-right">
        <el-button @click="showManageAccounts = true">管理账户</el-button>
      </div>
    </div>

    <!-- Stats -->
    <div v-if="currentAccount" class="ba-stats">
      <div class="ba-stat" style="border-left-color:#4f6ef7;">
        <span class="ba-stat-label">{{ currentAccount.bank_name }}</span>
        <span class="ba-stat-value">{{ formatMoney(currentAccount.balance) }}</span>
        <span class="ba-stat-sub">当前余额</span>
      </div>
      <div class="ba-stat" style="border-left-color:#67c23a;">
        <span class="ba-stat-label">本期收入</span>
        <span class="ba-stat-value c-success">{{ formatMoney(periodInflow) }}</span>
      </div>
      <div class="ba-stat" style="border-left-color:#f56c6c;">
        <span class="ba-stat-label">本期支出</span>
        <span class="ba-stat-value c-danger">{{ formatMoney(periodOutflow) }}</span>
      </div>
    </div>

    <!-- Transactions -->
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">银行流水</span>
          <span style="font-size:12px;color:#c9cdd4;">由采购付款、销售收款、费用支出等业务自动生成</span>
        </div>
      </template>
      <div class="filter-bar">
        <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" @change="loadTransactions" />
      </div>
      <el-table :data="transactions" style="width:100%">
        <template #empty><el-empty description="暂无流水" /></template>
        <el-table-column prop="transaction_date" label="日期" min-width="110">
          <template #default="{ row }">{{ formatDate(row.transaction_date) }}</template>
        </el-table-column>
        <el-table-column prop="reference_no" label="流水号" min-width="140" />
        <el-table-column prop="transaction_type" label="类型" min-width="70" align="center">
          <template #default="{ row }">
            <span class="status-badge" :class="row.transaction_type === 'inflow' ? 'success' : 'danger'">
              {{ row.transaction_type === 'inflow' ? '收入' : '支出' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="金额" min-width="120" align="right">
          <template #default="{ row }">
            <span :style="{ color: row.transaction_type === 'inflow' ? '#67c23a' : '#f56c6c', fontWeight: 600 }">
              {{ row.transaction_type === 'inflow' ? '+' : '-' }}{{ formatMoney(row.amount) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="balance_after" label="余额" min-width="120" align="right">
          <template #default="{ row }">{{ formatMoney(row.balance_after) }}</template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="160" />
      </el-table>
    </el-card>

    <!-- Manage Accounts Dialog -->
    <el-dialog v-model="showManageAccounts" title="管理银行账户" width="600px">
      <div class="ba-list">
        <div v-for="acc in accounts" :key="acc.id" class="ba-list-item">
          <div class="ba-list-info">
            <div class="ba-list-name">{{ acc.bank_name }}</div>
            <div class="ba-list-number">{{ maskAccount(acc.account_number) }}</div>
          </div>
          <div class="ba-list-balance">{{ formatMoney(acc.balance) }}</div>
          <el-button size="small" link type="primary" @click="editAccount(acc)">编辑</el-button>
          <el-popconfirm title="确定删除？" @confirm="deleteAccount(acc.id)">
            <template #reference><el-button size="small" link type="danger">删除</el-button></template>
          </el-popconfirm>
        </div>
        <div class="ba-list-add" @click="openCreateAccount">
          <el-icon><Plus /></el-icon> 添加银行账户
        </div>
      </div>
    </el-dialog>

    <!-- Account Form Dialog -->
    <el-dialog v-model="accountDialogVisible" :title="editingAccountId ? '编辑银行账户' : '新增银行账户'" width="500px">
      <el-form :model="accountForm" :rules="accountRules" ref="accountFormRef" label-width="0">
        <div class="ba-group" style="border-left-color:#4f6ef7;">
          <div class="ba-group-header"><span class="ba-group-tag" style="background:#eef1ff;color:#4f6ef7;">账户信息</span></div>
          <div class="ba-group-body">
            <div class="ba-field"><span class="ba-label" style="min-width:80px;">银行名称</span><el-input v-model="accountForm.bank_name" /></div>
            <div class="ba-field"><span class="ba-label" style="min-width:80px;">账号</span><el-input v-model="accountForm.account_number" /></div>
            <div class="ba-field"><span class="ba-label" style="min-width:80px;">余额</span><el-input-number v-model="accountForm.balance" :precision="2" :min="0" style="width:100%" controls-position="right" /></div>
            <div class="ba-field"><span class="ba-label" style="min-width:80px;">描述</span><el-input v-model="accountForm.description" /></div>
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="accountDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveAccount">{{ editingAccountId ? '保存' : '创建' }}</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import bankAccountsApi from '../api/bankAccounts'
import bankTxApi from '../api/bankTransactions'
import { formatMoney, formatDate } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../utils/errorHandler'

const loading = ref(false)
const accounts = ref([])
const transactions = ref([])
const currentAccountId = ref(null)
const dateRange = ref([])

const showManageAccounts = ref(false)
const accountDialogVisible = ref(false)
const editingAccountId = ref(null)
const accountFormRef = ref(null)
const accountForm = ref({ bank_name: '', account_number: '', balance: 0, description: '' })
const accountRules = {
  bank_name: [{ required: true, message: '请输入银行名称', trigger: 'blur' }],
  account_number: [{ required: true, message: '请输入账号', trigger: 'blur' }],
}

const currentAccount = computed(() => accounts.value.find(a => a.id === currentAccountId.value))

const periodInflow = computed(() =>
  transactions.value.filter(t => t.transaction_type === 'inflow').reduce((s, t) => s + Number(t.amount || 0), 0)
)
const periodOutflow = computed(() =>
  transactions.value.filter(t => t.transaction_type === 'outflow').reduce((s, t) => s + Number(t.amount || 0), 0)
)

const maskAccount = (num) => {
  if (!num) return ''
  return num.length > 4 ? '**** **** **** ' + num.slice(-4) : num
}

const loadAccounts = async () => {
  try {
    const res = await bankAccountsApi.getBankAccounts()
    accounts.value = res.items || []
    if (!currentAccountId.value && accounts.value.length) currentAccountId.value = accounts.value[0].id
  } catch (e) { handleError(e, { defaultMsg: '加载银行账户失败，请检查网络连接' }) }
}

const loadTransactions = async () => {
  if (!currentAccountId.value) { transactions.value = []; return }
  loading.value = true
  try {
    const params = {}
    if (dateRange.value?.length === 2) { params.start_date = dateRange.value[0]; params.end_date = dateRange.value[1] }
    const res = await bankTxApi.getBankTransactions(currentAccountId.value, params)
    transactions.value = res.items || []
  } catch (e) { handleError(e, { defaultMsg: '加载流水失败，请检查网络连接' }) }
  finally { loading.value = false }
}

const onAccountChange = () => { loadTransactions() }

const openCreateTx = () => {
  txForm.value = { bank_account_id: currentAccountId.value, transaction_type: 'inflow', amount: 0, transaction_date: new Date().toISOString().split('T')[0], reference_no: '', counterparty: '', purpose: '', description: '收款' }
  txDialogVisible.value = true
}

const saveTransaction = async () => {
  if (!txFormRef.value) return
  const valid = await txFormRef.value.validate().catch(() => false)
  if (!valid) return
  try {
    await bankAccountsApi.deleteBankAccount(id)
    ElMessage.success('已删除')
    loadAccounts()
  } catch (e) { handleError(e, { defaultMsg: '删除失败，请检查该账户是否有关联流水' }) }
}

const openCreateAccount = () => {
  editingAccountId.value = null
  accountForm.value = { bank_name: '', account_number: '', balance: 0, description: '' }
  accountDialogVisible.value = true
}

const editAccount = (acc) => {
  editingAccountId.value = acc.id
  accountForm.value = { bank_name: acc.bank_name, account_number: acc.account_number, balance: acc.balance, description: acc.description || '' }
  accountDialogVisible.value = true
}

const saveAccount = async () => {
  if (!accountFormRef.value) return
  const valid = await accountFormRef.value.validate().catch(() => false)
  if (!valid) return
  try {
    if (editingAccountId.value) {
      await bankAccountsApi.updateBankAccount(editingAccountId.value, accountForm.value)
      ElMessage.success('更新成功')
    } else {
      await bankAccountsApi.createBankAccount(accountForm.value)
      ElMessage.success('创建成功')
    }
    accountDialogVisible.value = false
    loadAccounts()
  } catch (e) { handleError(e, { defaultMsg: '保存失败，请检查输入数据是否正确' }) }
}

const deleteAccount = async (id) => {
  try { await bankAccountsApi.deleteBankAccount(id); ElMessage.success('已删除'); loadAccounts() }
  catch (e) { handleError(e, { defaultMsg: '删除失败，请检查该账户是否有关联流水' }) }
}

useAccountAwareData(async () => {
  await loadAccounts()
  if (currentAccountId.value) await loadTransactions()
})
</script>

<style scoped>
.ba-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.ba-header-left { display: flex; align-items: center; gap: 12px; }
.ba-header-right { display: flex; gap: 8px; }
.ba-opt { display: flex; justify-content: space-between; align-items: center; width: 100%; padding: 0 4px; }
.ba-opt-balance { font-weight: 600; color: #4f6ef7; font-family: 'Consolas', 'Monaco', monospace; }

.ba-stats { display: flex; gap: 12px; margin-bottom: 20px; }
.ba-stat {
  flex: 1; background: #fafafa; border: 1px solid #f0f0f0; border-left: 4px solid;
  border-radius: 12px; padding: 14px 16px; display: flex; flex-direction: column; gap: 2px;
}
.ba-stat-label { font-size: 12px; color: #86909c; font-weight: 500; }
.ba-stat-value { font-size: 26px; font-weight: 700; letter-spacing: -0.5px; }
.ba-stat-sub { font-size: 12px; color: #c9cdd4; }

.ba-list { display: flex; flex-direction: column; gap: 8px; }
.ba-list-item {
  display: flex; align-items: center; gap: 12px;
  padding: 12px; background: #fafafa; border: 1px solid #f0f0f0; border-radius: 10px;
}
.ba-list-info { flex: 1; }
.ba-list-name { font-size: 14px; font-weight: 600; color: #1d2129; }
.ba-list-number { font-size: 12px; color: #86909c; font-family: 'Consolas', 'Monaco', monospace; }
.ba-list-balance { font-size: 16px; font-weight: 700; color: #1d2129; font-family: 'Consolas', 'Monaco', monospace; margin-right: 8px; }
.ba-list-add {
  display: flex; align-items: center; justify-content: center; gap: 6px;
  padding: 14px; border: 2px dashed #e0e0e0; border-radius: 10px; cursor: pointer;
  font-size: 14px; color: #86909c; transition: all 0.2s;
}
.ba-list-add:hover { border-color: #4f6ef7; color: #4f6ef7; background: #f4f6ff; }

.ba-group { background: #fafafa; border: 1px solid #f0f0f0; border-left: 4px solid; border-radius: 12px; overflow: hidden; }
.ba-group-header { padding: 12px 16px 4px; }
.ba-group-tag { display: inline-block; padding: 2px 12px; border-radius: 9999px; font-size: 12px; font-weight: 600; letter-spacing: 0.5px; }
.ba-group-body { padding: 4px 16px 12px; display: flex; flex-direction: column; gap: 10px; }
.ba-field { display: flex; align-items: center; gap: 12px; }
.ba-label { font-size: 13px; color: #4e5969; flex-shrink: 0; }
</style>
