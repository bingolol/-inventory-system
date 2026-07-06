<template>
  <div>
    <div class="row">
      <div class="c4"><div class="stat-mini"><span class="stat-mini-label">本月付款</span><span class="stat-mini-value" style="color:var(--danger);">{{ formatMoney(monthTotal) }}</span></div></div>
      <div class="c4"><div class="stat-mini"><span class="stat-mini-label">筛选合计</span><span class="stat-mini-value" style="color:var(--primary);">{{ formatMoney(totalAmount) }}</span></div></div>
      <div class="c4"><div class="stat-mini"><span class="stat-mini-label">记录数</span><span class="stat-mini-value" style="color:var(--success);">{{ payments.length }} 笔</span></div></div>
    </div>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">付款管理</span>
          <div class="card-header-actions">
            <el-button type="primary" @click="openCreateDialog"><el-icon><Plus /></el-icon> 新增付款</el-button>
          </div>
        </div>
      </template>
      <el-table :data="payments" stripe style="width:100%" v-loading="loading">
        <template #empty><el-empty description="暂无付款记录" /></template>
        <el-table-column prop="payment_date" label="日期" min-width="110">
          <template #default="{ row }">{{ formatDate(row.payment_date) }}</template>
        </el-table-column>
        <el-table-column label="付款类型" min-width="100">
          <template #default="{ row }"><el-tag size="small">{{ row.payment_type }}</el-tag></template>
        </el-table-column>
        <el-table-column label="金额" min-width="120" align="right">
          <template #default="{ row }"><span class="money" style="color:var(--danger);">-{{ formatMoney(row.amount) }}</span></template>
        </el-table-column>
        <el-table-column prop="payment_method" label="方式" min-width="80" align="center">
          <template #default="{ row }"><span class="status-badge" :class="row.payment_method==='company'?'primary':'warning'">{{ row.payment_method==='company'?'公司账户':'个人垫付' }}</span></template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column prop="created_at" label="创建时间" min-width="130">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-popconfirm title="确定冲红此付款？" @confirm="handleReverse(row)">
              <template #reference><el-button size="small" link type="danger">冲红</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="新增付款" width="500px">
      <el-form :model="paymentForm" label-width="0">
        <div class="fg" style="border-left-color:var(--danger);">
          <div class="fgh"><span class="fgt" style="background:var(--danger-light);color:var(--danger);">付款信息</span></div>
          <div class="fgb">
            <div class="ff"><span class="fl" style="min-width:80px;">付款日期</span><el-date-picker v-model="paymentForm.payment_date" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width:100%;" /></div>
            <div class="ff"><span class="fl" style="min-width:80px;">付款金额</span><el-input v-model.number="paymentForm.amount" /></div>
            <div class="ff"><span class="fl" style="min-width:80px;">付款类型</span><el-select v-model="paymentForm.payment_type" style="width:100%">
              <el-option label="采购付款" value="purchase" /><el-option label="费用付款" value="expense" /><el-option label="工资" value="salary" /><el-option label="缴税" value="tax" />
            </el-select></div>
            <div class="ff"><span class="fl" style="min-width:80px;">关联类型</span><el-select v-model="paymentForm.related_entity_type" style="width:100%">
              <el-option label="采购单" value="purchase_order" /><el-option label="费用" value="expense" /><el-option label="税费" value="tax_payable" />
            </el-select></div>
            <div class="ff" v-if="paymentForm.related_entity_type==='purchase_order'"><span class="fl" style="min-width:80px;">关联采购单</span><el-select v-model="paymentForm.related_entity_id" filterable style="width:100%" placeholder="选择采购单"><el-option v-for="po in purchaseOrders" :key="po.id" :label="`${po.order_no} - ¥${po.total_price}`" :value="po.id" /></el-select></div>
            <div class="ff" v-else-if="paymentForm.related_entity_type==='expense'"><span class="fl" style="min-width:80px;">关联费用</span><el-select v-model="paymentForm.related_entity_id" filterable style="width:100%" placeholder="选择费用"><el-option v-for="e in expenses" :key="e.id" :label="`${e.category} - ¥${e.amount}`" :value="e.id" /></el-select></div>
            <div class="ff"><span class="fl" style="min-width:80px;">付款方式</span><el-select v-model="paymentForm.payment_method" style="width:100%"><el-option label="公司账户" value="company" /><el-option label="个人垫付" value="private_advance" /></el-select></div>
            <div class="ff"><span class="fl" style="min-width:80px;">银行账户</span><el-select v-model="paymentForm.bank_account_id" clearable style="width:100%" placeholder="选择银行账户（可选）"><el-option v-for="ba in bankAccounts" :key="ba.id" :label="ba.bank_name" :value="ba.id" /></el-select></div>
            <div class="ff"><span class="fl" style="min-width:80px;">描述</span><el-input v-model="paymentForm.description" /></div>
          </div>
        </div>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" @click="savePayment">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import paymentsApi from '../api/payments'
import ordersApi from '../api/orders'
import expensesApi from '../api/expenses'
import bankAccountsApi from '../api/bankAccounts'
import { formatMoney, formatDate, formatDateTime } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../utils/errorHandler'

const payments = ref([])
const purchaseOrders = ref([])
const expenses = ref([])
const bankAccounts = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const paymentForm = ref({
  payment_type: 'purchase', related_entity_type: 'purchase_order', related_entity_id: null,
  amount: 0, payment_method: 'company', payment_date: new Date().toISOString().replace('Z', ''),
  bank_account_id: null, description: ''
})

const totalAmount = computed(() => payments.value.reduce((s, e) => s + (Number(e.amount) || 0), 0))
const monthTotal = computed(() => {
  const n = new Date()
  return payments.value.filter(e => { if (!e.payment_date) return false; const d = new Date(e.payment_date); return !isNaN(d.getTime()) && d.getMonth()===n.getMonth() && d.getFullYear()===n.getFullYear() }).reduce((s,e) => s+(Number(e.amount)||0), 0)
})

const loadPayments = async () => {
  loading.value = true
  try {
    const r = await paymentsApi.getPayments({ limit: 200 })
    payments.value = r?.items || []
  } catch (e) { handleError(e, { defaultMsg: '获取付款列表失败' }); payments.value = [] }
  finally { loading.value = false }
}

const loadReferences = async () => {
  try {
    const [poR, expR, baR] = await Promise.all([
      ordersApi.getPurchases({ limit: 200, status: 'completed' }),
      expensesApi.getExpenses({ limit: 200 }),
      bankAccountsApi.getBankAccounts()
    ])
    purchaseOrders.value = (poR?.items || []).filter(o => o.payment_status === 'unpaid')
    expenses.value = (expR?.items || []).filter(e => e.payment_status === 'unpaid')
    bankAccounts.value = baR?.items || []
  } catch (e) { console.error('[Payments] 加载引用数据失败', e) }
}

const openCreateDialog = () => {
  paymentForm.value = {
    payment_type: 'purchase', related_entity_type: 'purchase_order', related_entity_id: null,
    amount: 0, payment_method: 'company', payment_date: new Date().toISOString().replace('Z', ''),
    bank_account_id: null, description: ''
  }
  dialogVisible.value = true
  loadReferences()
}

const savePayment = async () => {
  try {
    await paymentsApi.createPayment(paymentForm.value)
    ElMessage.success('付款创建成功')
    dialogVisible.value = false
    loadPayments()
  } catch (e) { handleError(e, { defaultMsg: '创建付款失败' }) }
}

const handleReverse = async (row) => {
  try {
    await paymentsApi.reversePayment(row.id)
    ElMessage.success('付款已冲红')
    loadPayments()
  } catch (e) { handleError(e, { defaultMsg: '冲红失败' }) }
}

useAccountAwareData(() => { loadPayments() })
</script>

<style scoped>
.row { display:flex; gap:16px; margin-bottom:20px; }
.c4 { flex:1; }
.stat-mini { background:var(--bg-card); border:1px solid var(--border-light); border-left:4px solid var(--primary); border-radius:12px; padding:16px 20px; }
.stat-mini-label { display:block; font-size:13px; color:var(--text-secondary); font-weight:500; margin-bottom:4px; }
.stat-mini-value { font-size:26px; font-weight:700; letter-spacing:-0.5px; }
.fg { background:var(--bg-elevated); border:1px solid var(--border-light); border-left:4px solid; border-radius:12px; overflow:hidden; }
.fgh { padding:12px 16px 4px; }
.fgt { display:inline-block; padding:2px 12px; border-radius:9999px; font-size:12px; font-weight:600; }
.fgb { padding:4px 16px 12px; display:flex; flex-direction:column; gap:10px; }
.ff { display:flex; align-items:center; gap:12px; }
.fl { font-size:13px; color:var(--text-regular); flex-shrink:0; }
</style>
