<template>
  <div>
    <StatCards :items="[
      { label: '本月付款', value: formatMoney(monthTotal), color: 'danger' },
      { label: '筛选合计', value: formatMoney(totalAmount), color: 'primary' },
      { label: '记录数', value: payments.length + ' 笔', color: 'success' }
    ]" />

    <el-card shadow="never">
      <template #header>
        <PageHeader title="付款管理">
          <template #actions>
            <el-button type="primary" @click="openCreateDialog"><el-icon><Plus /></el-icon> 新增付款</el-button>
          </template>
        </PageHeader>
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
          <template #default="{ row }"><StatusTag :status="row.payment_method" type="payment_method" /></template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column prop="created_at" label="创建时间" min-width="130">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <ActionColumn :actions="[
              { key: 'reverse', label: '冲红', type: 'danger', confirm: '确定冲红此付款？' }
            ]" @click="(key) => key === 'reverse' && handleReverse(row)" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="新增付款" width="500px">
      <el-form :model="paymentForm" label-width="0">
        <FormGroup title="付款信息" color="danger">
          <FormField label="付款日期" label-width="80px"><el-date-picker v-model="paymentForm.payment_date" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width:100%;" /></FormField>
          <FormField label="付款金额" label-width="80px"><el-input v-model.number="paymentForm.amount" /></FormField>
          <FormField label="付款类型" label-width="80px"><el-select v-model="paymentForm.payment_type" style="width:100%">
            <el-option label="采购付款" value="purchase" /><el-option label="费用付款" value="expense" /><el-option label="工资" value="salary" /><el-option label="缴税" value="tax" />
          </el-select></FormField>
          <FormField label="关联类型" label-width="80px"><el-select v-model="paymentForm.related_entity_type" style="width:100%">
            <el-option label="采购单" value="purchase_order" /><el-option label="费用" value="expense" /><el-option label="税费" value="tax_payable" />
          </el-select></FormField>
          <FormField label="关联采购单" label-width="80px" v-if="paymentForm.related_entity_type==='purchase_order'"><el-select v-model="paymentForm.related_entity_id" filterable style="width:100%" placeholder="选择采购单"><el-option v-for="po in purchaseOrders" :key="po.id" :label="`${po.order_no} - ¥${po.total_price}`" :value="po.id" /></el-select></FormField>
          <FormField label="关联费用" label-width="80px" v-else-if="paymentForm.related_entity_type==='expense'"><el-select v-model="paymentForm.related_entity_id" filterable style="width:100%" placeholder="选择费用"><el-option v-for="e in expenses" :key="e.id" :label="`${e.category} - ¥${e.amount}`" :value="e.id" /></el-select></FormField>
          <FormField label="付款方式" label-width="80px"><el-select v-model="paymentForm.payment_method" style="width:100%"><el-option label="公司账户" value="company" /><el-option label="个人垫付" value="private_advance" /></el-select></FormField>
          <FormField label="银行账户" label-width="80px"><el-select v-model="paymentForm.bank_account_id" clearable style="width:100%" placeholder="选择银行账户（可选）"><el-option v-for="ba in bankAccounts" :key="ba.id" :label="ba.bank_name" :value="ba.id" /></el-select></FormField>
          <FormField label="描述" label-width="80px"><el-input v-model="paymentForm.description" /></FormField>
        </FormGroup>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" @click="savePayment">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import StatCards from '../components/StatCards.vue'
import PageHeader from '../components/PageHeader.vue'
import FormGroup from '../components/FormGroup.vue'
import FormField from '../components/FormField.vue'
import StatusTag from '../components/StatusTag.vue'
import ActionColumn from '../components/ActionColumn.vue'
import paymentsApi from '../api/payments'
import ordersApi from '../api/orders'
import expensesApi from '../api/expenses'
import bankAccountsApi from '../api/bankAccounts'
import { formatMoney, formatDate, formatDateTime } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../utils/errorHandler'
import { nowLocal, isSameMonth } from '../utils/date'

const payments = ref([])
const purchaseOrders = ref([])
const expenses = ref([])
const bankAccounts = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const paymentForm = ref({
  payment_type: 'purchase', related_entity_type: 'purchase_order', related_entity_id: null,
  amount: 0, payment_method: 'company', payment_date: nowLocal(),
  bank_account_id: null, description: ''
})

const totalAmount = computed(() => payments.value.reduce((s, e) => s + (Number(e.amount) || 0), 0))
const monthTotal = computed(() => {
  return payments.value.filter(e => isSameMonth(e.payment_date)).reduce((s,e) => s+(Number(e.amount)||0), 0)
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
    amount: 0, payment_method: 'company', payment_date: nowLocal(),
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
/* 样式已集中到 global.css */
</style>
