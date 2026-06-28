<template>
  <div v-loading="loading">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px;">
      <el-select v-model="currentAccountId" placeholder="选择银行账户" style="width:240px;" @change="onAccountChange">
        <el-option v-for="acc in accounts" :key="acc.id" :label="`${acc.bank_name} (${maskAccount(acc.account_number)})`" :value="acc.id">
          <div style="display:flex;justify-content:space-between;align-items:center;width:100%;"><span>{{ acc.bank_name }}</span><span style="font-weight:600;color:#4f62c0;">{{ formatMoney(acc.balance) }}</span></div>
        </el-option>
      </el-select>
      <el-button size="small" @click="showManageAccounts=true">管理账户</el-button>
    </div>

    <div v-if="currentAccount" class="row" style="margin-bottom:16px;">
      <div class="c4"><div class="c"><div class="cl">{{ currentAccount.bank_name }}</div><div class="cv">{{ formatMoney(currentAccount.balance) }}</div><div class="cs">当前余额</div></div></div>
      <div class="c4"><div class="c"><div class="cl">本期收入</div><div class="cv c-success">{{ formatMoney(periodInflow) }}</div><div class="cs">期间内收款合计</div></div></div>
      <div class="c4"><div class="c"><div class="cl">本期支出</div><div class="cv c-danger">{{ formatMoney(periodOutflow) }}</div><div class="cs">期间内付款合计</div></div></div>
    </div>

    <div class="box">
      <div class="bh"><span class="bt">银行流水</span><span style="font-size:11px;color:#c9cdd4;">由业务自动生成</span></div>
      <table class="tbl" v-if="transactions.length">
        <tr><th>日期</th><th>流水号</th><th style="width:60px;">类型</th><th style="width:120px;">金额</th><th style="width:120px;">余额</th><th>描述</th></tr>
        <tr v-for="t in transactions" :key="t.id">
          <td>{{ formatDate(t.transaction_date) }}</td>
          <td style="color:#86909c;">{{ t.reference_no }}</td>
          <td><span class="bg" :class="t.transaction_type==='inflow'?'bs':'bd'">{{ t.transaction_type==='inflow'?'收入':'支出' }}</span></td>
          <td :style="{ color:t.transaction_type==='inflow'?'#67c23a':'#f56c6c', fontWeight:600 }">{{ t.transaction_type==='inflow'?'+':'-' }}{{ formatMoney(t.amount) }}</td>
          <td style="font-family:'Consolas','Monaco',monospace;">{{ formatMoney(t.balance_after) }}</td>
          <td style="color:#86909c;">{{ t.description||'-' }}</td>
        </tr>
      </table>
      <div v-else style="padding:24px 0;text-align:center;color:#c9cdd4;font-size:13px;">暂无流水记录</div>
    </div>

    <el-dialog v-model="showManageAccounts" title="管理银行账户" width="600px">
      <div style="display:flex;flex-direction:column;gap:8px;">
        <div v-for="acc in accounts" :key="acc.id" style="display:flex;align-items:center;gap:12px;padding:10px 12px;background:#f8f9fa;border-radius:6px;">
          <div style="flex:1;"><div style="font-size:14px;font-weight:600;color:#1d2129;">{{ acc.bank_name }}</div><div style="font-size:12px;color:#86909c;">{{ maskAccount(acc.account_number) }}</div></div>
          <div style="font-size:16px;font-weight:700;">{{ formatMoney(acc.balance) }}</div>
          <el-button size="small" link type="primary" @click="editAccount(acc)">编辑</el-button>
          <el-popconfirm title="确定删除？" @confirm="deleteAccount(acc.id)"><template #reference><el-button size="small" link type="danger">删除</el-button></template></el-popconfirm>
        </div>
        <div style="display:flex;align-items:center;justify-content:center;gap:6px;padding:12px;border:2px dashed #edf0f5;border-radius:8px;cursor:pointer;color:#86909c;font-size:13px;" @click="openCreateAccount">+ 添加银行账户</div>
      </div>
    </el-dialog>

    <el-dialog v-model="accountDialogVisible" :title="editingAccountId?'编辑银行账户':'新增银行账户'" width="460px">
      <el-form :model="accountForm" :rules="accountRules" ref="accountFormRef" label-width="0">
        <div class="fg" style="border-left-color:#4f62c0;">
          <div class="fgh"><span class="fgt" style="background:#eef1ff;color:#4f62c0;">账户信息</span></div>
          <div class="fgb">
            <div class="ff"><span class="fl" style="min-width:70px;">银行名称</span><el-input v-model="accountForm.bank_name" /></div>
            <div class="ff"><span class="fl" style="min-width:70px;">账号</span><el-input v-model="accountForm.account_number" /></div>
            <div class="ff"><span class="fl" style="min-width:70px;">余额</span><el-input-number v-model="accountForm.balance" :precision="2" :min="0" style="width:100%;" controls-position="right" /></div>
            <div class="ff"><span class="fl" style="min-width:70px;">描述</span><el-input v-model="accountForm.description" /></div>
          </div>
        </div>
      </el-form>
      <template #footer><el-button @click="accountDialogVisible=false">取消</el-button><el-button type="primary" @click="saveAccount">{{ editingAccountId?'保存':'创建' }}</el-button></template>
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
const showManageAccounts = ref(false)
const accountDialogVisible = ref(false)
const editingAccountId = ref(null)
const accountFormRef = ref(null)
const accountForm = ref({ bank_name:'', account_number:'', balance:0, description:'' })
const accountRules = { bank_name:[{required:true,message:'请输入银行名称',trigger:'blur'}], account_number:[{required:true,message:'请输入账号',trigger:'blur'}] }

const currentAccount = computed(() => accounts.value.find(a => a.id === currentAccountId.value))
const periodInflow = computed(() => transactions.value.filter(t => t.transaction_type==='inflow').reduce((s,t) => s+Number(t.amount||0),0))
const periodOutflow = computed(() => transactions.value.filter(t => t.transaction_type==='outflow').reduce((s,t) => s+Number(t.amount||0),0))
const maskAccount = (num) => num ? (num.length>4 ? '****'+num.slice(-4) : num) : ''

const loadAccounts = async () => {
  try { const r = await bankAccountsApi.getBankAccounts(); accounts.value = r.items||[]; if (!currentAccountId.value && accounts.value.length) currentAccountId.value = accounts.value[0].id }
  catch (e) { handleError(e, { defaultMsg:'加载银行账户失败' }) }
}
const loadTransactions = async () => {
  if (!currentAccountId.value) { transactions.value=[]; return }
  loading.value = true
  try { const r = await bankTxApi.getBankTransactions(currentAccountId.value, {limit:100}); transactions.value = r.items||[] }
  catch (e) { handleError(e, { defaultMsg:'加载流水失败' }) }
  finally { loading.value = false }
}
const onAccountChange = () => { loadTransactions() }

const openCreateAccount = () => { editingAccountId.value=null; accountForm.value={bank_name:'',account_number:'',balance:0,description:''}; accountDialogVisible.value=true }
const editAccount = (acc) => { editingAccountId.value=acc.id; accountForm.value={bank_name:acc.bank_name,account_number:acc.account_number,balance:acc.balance,description:acc.description||''}; accountDialogVisible.value=true }

const saveAccount = async () => {
  if (!accountFormRef.value) return
  const valid = await accountFormRef.value.validate().catch(()=>false)
  if (!valid) return
  try {
    if (editingAccountId.value) { await bankAccountsApi.updateBankAccount(editingAccountId.value, accountForm.value); ElMessage.success('更新成功') }
    else { await bankAccountsApi.createBankAccount(accountForm.value); ElMessage.success('创建成功') }
    accountDialogVisible.value=false; loadAccounts()
  } catch (e) { handleError(e, { defaultMsg:'保存失败' }) }
}
const deleteAccount = async (id) => {
  try { await bankAccountsApi.deleteBankAccount(id); ElMessage.success('已删除'); loadAccounts() }
  catch (e) { handleError(e, { defaultMsg:'删除失败' }) }
}

useAccountAwareData(async () => { await loadAccounts(); if (currentAccountId.value) await loadTransactions() })
</script>

<style scoped>
.row { display:flex; gap:12px; margin-bottom:16px; }
.c4 { flex:1; }
.c { background:#fff; border:1px solid #edf0f5; border-radius:10px; padding:14px 16px; }
.cl { font-size:12px; color:#4e5969; font-weight:500; margin-bottom:4px; }
.cv { font-size:24px; font-weight:700; letter-spacing:-0.5px; margin-bottom:2px; }
.cs { font-size:12px; color:#86909c; }

.box { background:#fff; border:1px solid #edf0f5; border-radius:10px; padding:16px; }
.bh { display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }
.bt { font-size:13px; font-weight:600; color:#1d2129; }

.tbl { width:100%; border-collapse:collapse; }
.tbl th { text-align:left; padding:8px 10px; font-size:11px; font-weight:600; color:#86909c; border-bottom:1px solid #f5f6f8; }
.tbl td { padding:8px 10px; font-size:13px; color:#4e5969; border-bottom:1px solid #f8f9fa; }
.tbl tr:last-child td { border:none; }

.bg { display:inline-block; padding:1px 8px; border-radius:4px; font-size:11px; font-weight:500; }
.bs { background:#f0f9eb; color:#67c23a; }
.bd { background:#fef0f0; color:#f56c6c; }

.fg { background:#fafafa; border:1px solid #f0f0f0; border-left:4px solid; border-radius:12px; overflow:hidden; }
.fgh { padding:12px 16px 4px; }
.fgt { display:inline-block; padding:2px 12px; border-radius:9999px; font-size:12px; font-weight:600; }
.fgb { padding:4px 16px 12px; display:flex; flex-direction:column; gap:10px; }
.ff { display:flex; align-items:center; gap:12px; }
.fl { font-size:13px; color:#4e5969; flex-shrink:0; }

.c-success { color:#67c23a; }
.c-danger { color:#f56c6c; }
</style>
