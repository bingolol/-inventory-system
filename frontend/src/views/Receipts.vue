<template>
  <div>
    <div class="row">
      <div class="c4"><div class="stat-mini"><span class="stat-mini-label">本月收款</span><span class="stat-mini-value" style="color:var(--success);">{{ formatMoney(monthTotal) }}</span></div></div>
      <div class="c4"><div class="stat-mini"><span class="stat-mini-label">筛选合计</span><span class="stat-mini-value" style="color:var(--primary);">{{ formatMoney(totalAmount) }}</span></div></div>
      <div class="c4"><div class="stat-mini"><span class="stat-mini-label">记录数</span><span class="stat-mini-value" style="color:var(--success);">{{ receipts.length }} 笔</span></div></div>
    </div>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">收款管理</span>
          <div class="card-header-actions">
            <el-button type="primary" @click="openCreateDialog"><el-icon><Plus /></el-icon> 新增收款</el-button>
          </div>
        </div>
      </template>
      <el-table :data="receipts" stripe style="width:100%" v-loading="loading">
        <template #empty><el-empty description="暂无收款记录" /></template>
        <el-table-column prop="receipt_date" label="日期" min-width="110">
          <template #default="{ row }">{{ formatDate(row.receipt_date) }}</template>
        </el-table-column>
        <el-table-column label="收款类型" min-width="100">
          <template #default="{ row }"><el-tag size="small">{{ row.receipt_type }}</el-tag></template>
        </el-table-column>
        <el-table-column label="金额" min-width="120" align="right">
          <template #default="{ row }"><span class="money" style="color:var(--success);">+{{ formatMoney(row.amount) }}</span></template>
        </el-table-column>
        <el-table-column prop="receipt_method" label="方式" min-width="80" align="center">
          <template #default="{ row }"><span class="status-badge" :class="row.receipt_method==='company'?'primary':'warning'">{{ row.receipt_method==='company'?'公司账户':'个人垫付' }}</span></template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column prop="created_at" label="创建时间" min-width="130">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-popconfirm title="确定冲红此收款？" @confirm="handleReverse(row)">
              <template #reference><el-button size="small" link type="danger">冲红</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="新增收款" width="500px">
      <el-form :model="receiptForm" label-width="0">
        <div class="fg" style="border-left-color:var(--success);">
          <div class="fgh"><span class="fgt" style="background:var(--success-light);color:var(--success);">收款信息</span></div>
          <div class="fgb">
            <div class="ff"><span class="fl" style="min-width:80px;">收款日期</span><el-date-picker v-model="receiptForm.receipt_date" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width:100%;" /></div>
            <div class="ff"><span class="fl" style="min-width:80px;">收款金额</span><el-input v-model.number="receiptForm.amount" /></div>
            <div class="ff"><span class="fl" style="min-width:80px;">收款类型</span><el-select v-model="receiptForm.receipt_type" style="width:100%"><el-option label="销售收款" value="sale" /></el-select></div>
            <div class="ff"><span class="fl" style="min-width:80px;">关联类型</span><el-select v-model="receiptForm.related_entity_type" style="width:100%"><el-option label="销售单" value="sale_order" /></el-select></div>
            <div class="ff"><span class="fl" style="min-width:80px;">关联单号</span><el-select v-model="receiptForm.related_entity_id" filterable style="width:100%" placeholder="选择销售单"><el-option v-for="so in saleOrders" :key="so.id" :label="`${so.order_no} - ¥${so.total_price}`" :value="so.id" /></el-select></div>
            <div class="ff"><span class="fl" style="min-width:80px;">收款方式</span><el-select v-model="receiptForm.receipt_method" style="width:100%"><el-option label="公司账户" value="company" /><el-option label="个人垫付" value="private_advance" /></el-select></div>
            <div class="ff"><span class="fl" style="min-width:80px;">银行账户</span><el-select v-model="receiptForm.bank_account_id" clearable style="width:100%" placeholder="选择银行账户（可选）"><el-option v-for="ba in bankAccounts" :key="ba.id" :label="ba.bank_name" :value="ba.id" /></el-select></div>
            <div class="ff"><span class="fl" style="min-width:80px;">描述</span><el-input v-model="receiptForm.description" /></div>
          </div>
        </div>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" @click="saveReceipt">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import receiptsApi from '../api/receipts'
import ordersApi from '../api/orders'
import bankAccountsApi from '../api/bankAccounts'
import { formatMoney, formatDate, formatDateTime } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../utils/errorHandler'

const receipts = ref([])
const saleOrders = ref([])
const bankAccounts = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const receiptForm = ref({
  receipt_type: 'sale', related_entity_type: 'sale_order', related_entity_id: null,
  amount: 0, receipt_method: 'company', receipt_date: new Date().toISOString().replace('Z', ''),
  bank_account_id: null, description: ''
})

const totalAmount = computed(() => receipts.value.reduce((s, e) => s + (Number(e.amount) || 0), 0))
const monthTotal = computed(() => {
  const n = new Date()
  return receipts.value.filter(e => { if (!e.receipt_date) return false; const d = new Date(e.receipt_date); return !isNaN(d.getTime()) && d.getMonth()===n.getMonth() && d.getFullYear()===n.getFullYear() }).reduce((s,e) => s+(Number(e.amount)||0), 0)
})

const loadReceipts = async () => {
  loading.value = true
  try {
    const r = await receiptsApi.getReceipts({ limit: 200 })
    receipts.value = r?.items || []
  } catch (e) { handleError(e, { defaultMsg: '获取收款列表失败' }); receipts.value = [] }
  finally { loading.value = false }
}

const loadSaleOrders = async () => {
  try {
    const r = await ordersApi.getSales({ limit: 200, status: 'completed' })
    saleOrders.value = (r?.items || []).filter(o => o.payment_status === 'unpaid')
  } catch (e) { console.error('[Receipts] 加载销售单失败', e) }
}

const loadBankAccounts = async () => {
  try {
    const r = await bankAccountsApi.getBankAccounts()
    bankAccounts.value = r?.items || []
  } catch (e) { console.error('[Receipts] 加载银行账户失败', e) }
}

const openCreateDialog = () => {
  receiptForm.value = {
    receipt_type: 'sale', related_entity_type: 'sale_order', related_entity_id: null,
    amount: 0, receipt_method: 'company', receipt_date: new Date().toISOString().replace('Z', ''),
    bank_account_id: null, description: ''
  }
  dialogVisible.value = true
  loadSaleOrders()
  loadBankAccounts()
}

const saveReceipt = async () => {
  try {
    await receiptsApi.createReceipt(receiptForm.value)
    ElMessage.success('收款创建成功')
    dialogVisible.value = false
    loadReceipts()
  } catch (e) { handleError(e, { defaultMsg: '创建收款失败' }) }
}

const handleReverse = async (row) => {
  try {
    await receiptsApi.reverseReceipt(row.id)
    ElMessage.success('收款已冲红')
    loadReceipts()
  } catch (e) { handleError(e, { defaultMsg: '冲红失败' }) }
}

useAccountAwareData(() => { loadReceipts() })
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
