<template>
  <div>
    <StatCards :items="[
      { label: mode==='receipt'?'本月收款':'本月付款', value: formatMoney(monthTotal), color: mode==='receipt'?'success':'danger' },
      { label: '筛选合计', value: formatMoney(totalAmount), color: 'primary' },
      { label: '记录数', value: items.length + ' 笔' }
    ]" />

    <el-card shadow="never">
      <template #header>
        <PageHeader title="资金流水">
          <template #actions>
            <div style="display:flex;gap:8px;align-items:center;">
              <el-radio-group v-model="mode" @change="onModeChange">
                <el-radio value="receipt">收款</el-radio>
                <el-radio value="payment">付款</el-radio>
              </el-radio-group>
              <el-button type="primary" @click="openCreateDialog"><el-icon><Plus /></el-icon> 新增{{ mode==='receipt'?'收款':'付款' }}</el-button>
            </div>
          </template>
        </PageHeader>
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
          <template #default="{ row }"><StatusTag :status="mode==='receipt'?row.receipt_method:row.payment_method" :type="mode==='receipt'?'receipt_method':'payment_method'" /></template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column prop="created_at" label="创建时间" min-width="130">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <ActionColumn :actions="[
              { key: 'reverse', label: '冲红', type: 'danger', confirm: `确定冲红此${mode==='receipt'?'收款':'付款'}？` }
            ]" @click="(key) => { if (key === 'reverse') handleReverse(row) }" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="`新增${mode==='receipt'?'收款':'付款'}`" width="500px">
      <el-form :model="form" label-width="0">
        <FormGroup :title="`${mode==='receipt'?'收款':'付款'}信息`" :color="mode==='receipt'?'success':'danger'">
          <FormField :label="`${mode==='receipt'?'收款':'付款'}日期`" label-width="80px"><el-date-picker v-model="form.date" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width:100%;" /></FormField>
          <FormField :label="`${mode==='receipt'?'收款':'付款'}金额`" label-width="80px"><el-input v-model.number="form.amount" /></FormField>
          <FormField :label="`${mode==='receipt'?'收款':'付款'}类型`" label-width="80px"><el-select v-model="form.entity_type" style="width:100%" @change="form.related_entity_id = null">
            <el-option v-for="opt in entityTypeOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select></FormField>
          <FormField label="关联单据" label-width="80px" v-if="showRelatedSelect"><el-select v-model="form.related_entity_id" filterable style="width:100%" :placeholder="`选择${relatedLabel}`"><el-option v-for="ref in references" :key="ref.key" :label="ref.label" :value="ref.id" /></el-select></FormField>
          <FormField label="结算方式" label-width="80px"><el-select v-model="form.method" style="width:100%"><el-option label="公司账户" value="company" /><el-option label="个人垫付" value="private_advance" /></el-select></FormField>
          <FormField label="银行账户" label-width="80px"><el-select v-model="form.bank_account_id" clearable style="width:100%" placeholder="选择银行账户（可选）"><el-option v-for="ba in bankAccounts" :key="ba.id" :label="ba.bank_name" :value="ba.id" /></el-select></FormField>
          <FormField label="描述" label-width="80px"><el-input v-model="form.description" /></FormField>
        </FormGroup>
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
import StatCards from '../components/StatCards.vue'
import PageHeader from '../components/PageHeader.vue'
import FormGroup from '../components/FormGroup.vue'
import FormField from '../components/FormField.vue'
import StatusTag from '../components/StatusTag.vue'
import ActionColumn from '../components/ActionColumn.vue'
import receiptsApi from '../api/receipts'
import paymentsApi from '../api/payments'
import ordersApi from '../api/orders'
import expensesApi from '../api/expenses'
import bankAccountsApi from '../api/bankAccounts'
import { formatMoney, formatDate, formatDateTime } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../utils/errorHandler'
import { nowLocal, isSameMonth } from '../utils/date'

const route = useRoute()
const mode = ref(route.query.tab === 'payment' ? 'payment' : 'receipt')
const items = ref([])
const saleReferences = ref([])
const purchaseReferences = ref([])
const expenseReferences = ref([])
const bankAccounts = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const form = ref(createEmptyForm())

function createEmptyForm() {
  return {
    date: nowLocal(),
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

const references = computed(() => {
  if (mode.value === 'receipt') return saleReferences.value
  if (form.value.entity_type === 'purchase') return purchaseReferences.value
  if (form.value.entity_type === 'expense') return expenseReferences.value
  return []
})

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
  return items.value.filter(e => {
    const d = mode.value === 'receipt' ? e.receipt_date : e.payment_date
    return isSameMonth(d)
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
      saleReferences.value = (r?.items || []).filter(o => o.payment_status === 'unpaid').map(o => ({ id: o.id, key: `sale-${o.id}`, label: `${o.order_no} - ¥${o.total_price}` }))
    } else {
      const [poR, expR] = await Promise.all([
        ordersApi.getPurchases({ limit: 200, status: 'completed' }),
        expensesApi.getExpenses({ limit: 200 })
      ])
      purchaseReferences.value = (poR?.items || []).filter(o => o.payment_status === 'unpaid').map(o => ({ id: o.id, key: `purchase-${o.id}`, label: `${o.order_no} - ¥${o.total_price}` }))
      expenseReferences.value = (expR?.items || []).filter(e => e.payment_status === 'unpaid').map(e => ({ id: e.id, key: `expense-${e.id}`, label: `${e.category} - ¥${e.amount}` }))
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
    if (['purchase', 'expense'].includes(form.value.entity_type) && !form.value.related_entity_id) {
      ElMessage.warning('请选择关联单据')
      return
    }

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
        payload.related_entity_id = form.value.related_entity_id || 0
      } else if (form.value.entity_type === 'salary') {
        payload.related_entity_type = 'expense'
        payload.related_entity_id = form.value.related_entity_id || 0
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
/* 样式已集中到 global.css */
</style>
