<template>
  <div>
    <div class="row">
      <div class="c4"><div class="stat-mini"><span class="stat-mini-label">{{ mode==='receipt'?'本月收款':'本月付款' }}</span><span class="stat-mini-value" :style="{color:mode==='receipt'?'var(--success)':'var(--danger)'}">{{ formatMoney(monthTotal) }}</span></div></div>
      <div class="c4"><div class="stat-mini"><span class="stat-mini-label">筛选合计</span><span class="stat-mini-value" style="color:var(--primary);">{{ formatMoney(totalAmount) }}</span></div></div>
      <div class="c4"><div class="stat-mini"><span class="stat-mini-label">记录数</span><span class="stat-mini-value">{{ items.length }} 笔</span></div></div>
    </div>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">资金流水</span>
          <div style="display:flex;gap:8px;align-items:center;">
            <el-radio-group v-model="mode" @change="onModeChange">
              <el-radio value="receipt">收款</el-radio>
              <el-radio value="payment">付款</el-radio>
            </el-radio-group>
            <el-button type="primary" @click="openCreateDialog"><el-icon><Plus /></el-icon> 新增{{ mode==='receipt'?'收款':'付款' }}</el-button>
          </div>
        </div>
      </template>
      <el-table :data="items" stripe style="width:100%" v-loading="loading">
        <template #empty><el-empty :description="`暂无${mode==='receipt'?'收款':'付款'}记录`" /></template>
        <el-table-column :prop="mode==='receipt'?'receipt_date':'payment_date'" label="日期" min-width="110">
          <template #default="{ row }">{{ formatDate(mode==='receipt'?row.receipt_date:row.payment_date) }}</template>
        </el-table-column>
        <el-table-column :label="mode==='receipt'?'收款类型':'付款类型'" min-width="100">
          <template #default="{ row }"><el-tag size="small">{{ mode==='receipt'?row.receipt_type:row.payment_type }}</el-tag></template>
        </el-table-column>
        <el-table-column label="金额" min-width="120" align="right">
          <template #default="{ row }"><span class="money" :style="{color:mode==='receipt'?'var(--success)':'var(--danger)'}">{{ mode==='receipt'?'+':'-' }}{{ formatMoney(row.amount) }}</span></template>
        </el-table-column>
        <el-table-column :prop="mode==='receipt'?'receipt_method':'payment_method'" label="方式" min-width="80" align="center">
          <template #default="{ row }"><span class="status-badge" :class="(mode==='receipt'?row.receipt_method:row.payment_method)==='company'?'primary':'warning'">{{ (mode==='receipt'?row.receipt_method:row.payment_method)==='company'?'公司账户':'个人垫付' }}</span></template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column prop="created_at" label="创建时间" min-width="130">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-popconfirm :title="`确定冲红此${mode==='receipt'?'收款':'付款'}？`" @confirm="handleReverse(row)">
              <template #reference><el-button size="small" link type="danger">冲红</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="`新增${mode==='receipt'?'收款':'付款'}`" width="500px">
      <el-form :model="form" label-width="0">
        <div class="fg" :style="{borderLeftColor:mode==='receipt'?'var(--success)':'var(--danger)'}">
          <div class="fgh"><span class="fgt" :style="mode==='receipt'?{background:'var(--success-light)',color:'var(--success)'}:{background:'var(--danger-light)',color:'var(--danger)'}">{{ mode==='receipt'?'收款':'付款' }}信息</span></div>
          <div class="fgb">
            <div class="ff"><span class="fl" style="min-width:80px;">{{ mode==='receipt'?'收款':'付款' }}日期</span><el-date-picker v-model="form.date" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width:100%;" /></div>
            <div class="ff"><span class="fl" style="min-width:80px;">{{ mode==='receipt'?'收款':'付款' }}金额</span><el-input v-model.number="form.amount" /></div>
            <div class="ff"><span class="fl" style="min-width:80px;">{{ mode==='receipt'?'收款':'付款' }}类型</span><el-select v-model="form.entity_type" style="width:100%">
              <el-option v-for="opt in entityTypeOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
            </el-select></div>
            <div class="ff" v-if="showRelatedSelect"><span class="fl" style="min-width:80px;">关联单据</span><el-select v-model="form.related_entity_id" filterable style="width:100%" :placeholder="`选择${relatedLabel}`"><el-option v-for="ref in references" :key="ref.id" :label="ref.label" :value="ref.id" /></el-select></div>
            <div class="ff"><span class="fl" style="min-width:80px;">结算方式</span><el-select v-model="form.method" style="width:100%"><el-option label="公司账户" value="company" /><el-option label="个人垫付" value="private_advance" /></el-select></div>
            <div class="ff"><span class="fl" style="min-width:80px;">银行账户</span><el-select v-model="form.bank_account_id" clearable style="width:100%" placeholder="选择银行账户（可选）"><el-option v-for="ba in bankAccounts" :key="ba.id" :label="ba.bank_name" :value="ba.id" /></el-select></div>
            <div class="ff"><span class="fl" style="min-width:80px;">描述</span><el-input v-model="form.description" /></div>
          </div>
        </div>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" @click="save">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import receiptsApi from '../api/receipts'
import paymentsApi from '../api/payments'
import ordersApi from '../api/orders'
import expensesApi from '../api/expenses'
import bankAccountsApi from '../api/bankAccounts'
import { formatMoney, formatDate, formatDateTime } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../utils/errorHandler'

const route = useRoute()
const mode = ref(route.query.tab === 'payment' ? 'payment' : 'receipt')
const items = ref([])
const references = ref([])
const bankAccounts = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const form = ref(createEmptyForm())

function createEmptyForm() {
  return {
    date: new Date().toISOString().replace('Z', ''),
    amount: 0,
    entity_type: mode.value === 'receipt' ? 'sale' : 'purchase',
    related_entity_id: null,
    method: 'company',
    bank_account_id: null,
    description: ''
  }
}

const entityTypeOptions = computed(() => {
  if (mode.value === 'receipt') return [{ label: '销售收款', value: 'sale' }]
  return [
    { label: '采购付款', value: 'purchase' },
    { label: '费用付款', value: 'expense' },
    { label: '工资', value: 'salary' },
    { label: '缴税', value: 'tax' },
  ]
})

const api = computed(() => mode.value === 'receipt' ? receiptsApi : paymentsApi)
const dateField = computed(() => mode.value === 'receipt' ? 'receipt_date' : 'payment_date')
const typeField = computed(() => mode.value === 'receipt' ? 'receipt_type' : 'payment_type')
const methodField = computed(() => mode.value === 'receipt' ? 'receipt_method' : 'payment_method')

const showRelatedSelect = computed(() => {
  return mode.value === 'receipt' || ['purchase', 'expense'].includes(form.value.entity_type)
})

const relatedLabel = computed(() => {
  if (mode.value === 'receipt') return '销售单'
  if (form.value.entity_type === 'purchase') return '采购单'
  if (form.value.entity_type === 'expense') return '费用'
  return ''
})

const totalAmount = computed(() => items.value.reduce((s, e) => s + (Number(e.amount) || 0), 0))
const monthTotal = computed(() => {
  const n = new Date()
  return items.value.filter(e => {
    const d = mode.value === 'receipt' ? e.receipt_date : e.payment_date
    if (!d) return false
    const dt = new Date(d)
    return !isNaN(dt.getTime()) && dt.getMonth() === n.getMonth() && dt.getFullYear() === n.getFullYear()
  }).reduce((s, e) => s + (Number(e.amount) || 0), 0)
})

const loadItems = async () => {
  loading.value = true
  try {
    const apiFn = mode.value === 'receipt' ? receiptsApi.getReceipts : paymentsApi.getPayments
    const r = await apiFn({ limit: 200 })
    items.value = r?.items || []
  } catch (e) { handleError(e, { defaultMsg: `获取${mode.value==='receipt'?'收款':'付款'}列表失败` }); items.value = [] }
  finally { loading.value = false }
}

const loadReferences = async () => {
  try {
    if (mode.value === 'receipt') {
      const r = await ordersApi.getSales({ limit: 200, status: 'completed' })
      references.value = (r?.items || []).filter(o => o.payment_status === 'unpaid').map(o => ({ id: o.id, label: `${o.order_no} - ¥${o.total_price}` }))
    } else {
      const [poR, expR] = await Promise.all([
        ordersApi.getPurchases({ limit: 200, status: 'completed' }),
        expensesApi.getExpenses({ limit: 200 })
      ])
      references.value = [
        ...(poR?.items || []).filter(o => o.payment_status === 'unpaid').map(o => ({ id: o.id, label: `${o.order_no} - ¥${o.total_price}` })),
        ...(expR?.items || []).filter(e => e.payment_status === 'unpaid').map(e => ({ id: e.id, label: `${e.category} - ¥${e.amount}` }))
      ]
    }
    const baR = await bankAccountsApi.getBankAccounts()
    bankAccounts.value = baR?.items || []
  } catch (e) { /* ignore */ }
}

const onModeChange = () => {
  form.value = createEmptyForm()
  loadItems()
}

const openCreateDialog = () => {
  form.value = createEmptyForm()
  dialogVisible.value = true
  loadReferences()
}

const save = async () => {
  try {
    const payload = {
      [dateField.value]: form.value.date,
      amount: form.value.amount,
      [typeField.value]: form.value.entity_type,
      [methodField.value]: form.value.method,
      bank_account_id: form.value.bank_account_id,
      description: form.value.description,
    }
    if (mode.value === 'receipt') {
      payload.related_entity_type = 'sale_order'
      payload.related_entity_id = form.value.related_entity_id
    } else {
      if (form.value.entity_type === 'purchase') {
        payload.related_entity_type = 'purchase_order'
        payload.related_entity_id = form.value.related_entity_id
      } else if (form.value.entity_type === 'expense') {
        payload.related_entity_type = 'expense'
        payload.related_entity_id = form.value.related_entity_id
      } else if (form.value.entity_type === 'tax') {
        payload.related_entity_type = 'tax_payable'
      }
    }
    if (mode.value === 'receipt') {
      await receiptsApi.createReceipt(payload)
    } else {
      await paymentsApi.createPayment(payload)
    }
    ElMessage.success(`${mode.value==='receipt'?'收款':'付款'}创建成功`)
    dialogVisible.value = false
    loadItems()
  } catch (e) { handleError(e, { defaultMsg: `创建${mode.value==='receipt'?'收款':'付款'}失败` }) }
}

const handleReverse = async (row) => {
  try {
    if (mode.value === 'receipt') {
      await receiptsApi.reverseReceipt(row.id)
    } else {
      await paymentsApi.reversePayment(row.id)
    }
    ElMessage.success(`${mode.value==='receipt'?'收款':'付款'}已冲红`)
    loadItems()
  } catch (e) { handleError(e, { defaultMsg: '冲红失败' }) }
}

useAccountAwareData(() => { loadItems() })
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
