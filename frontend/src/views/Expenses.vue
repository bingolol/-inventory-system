<template>
  <div>
    <StatCards :items="[
      { label: '本月费用', value: formatMoney(monthTotal), color: 'danger' },
      { label: '筛选合计', value: formatMoney(totalAmount), color: 'primary' },
      { label: '记录数', value: expenses.length + ' 笔', color: 'success' }
    ]" />

    <el-card shadow="never">
      <template #header>
        <PageHeader title="费用管理">
          <template #actions>
            <el-button type="primary" @click="openCreateDialog">
              <el-icon><Plus /></el-icon> 新增费用
            </el-button>
          </template>
        </PageHeader>
      </template>
      <FilterBar @search="getExpenses" @reset="resetFilter">
        <el-select v-model="filterForm.year" placeholder="年份" clearable style="width:120px;">
          <el-option v-for="y in years" :key="y" :label="y" :value="y" />
        </el-select>
        <template #extra-actions>
          <el-button size="small" @click="$router.push('/funds/transactions?tab=payment')"><el-icon><Plus /></el-icon> 付款管理</el-button>
        </template>
      </FilterBar>
      <el-table :data="expenses" stripe style="width:100%" v-loading="loading">
        <template #empty>
          <el-empty description="暂无费用记录" />
        </template>
        <el-table-column prop="expense_date" label="日期" min-width="110">
          <template #default="{ row }">{{ formatDate(row.expense_date) }}</template>
        </el-table-column>
        <el-table-column label="类别" min-width="100">
          <template #default="{ row }"><el-tag size="small">{{ row.category }}</el-tag></template>
        </el-table-column>
        <el-table-column label="功能分类" min-width="100">
          <template #default="{ row }"><StatusTag :status="row.functional_category || '管理费用'" type="functional_category" /></template>
        </el-table-column>
        <el-table-column label="金额" min-width="120" align="right">
          <template #default="{ row }">
            <span class="money" style="color:var(--danger);">-{{ formatMoney(row.amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="付款状态" min-width="90" align="center">
          <template #default="{ row }"><StatusTag :status="row.payment_status" type="payment_status" /></template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="160">
          <template #default="{ row }">{{ row.description || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" align="center">
          <template #default="{ row }">
            <ActionColumn :actions="[
              { key: 'edit', label: '编辑', type: 'primary' },
              { key: 'pay', label: '付款', type: 'danger', show: row.payment_status === 'unpaid' },
              { key: 'reverse', label: '冲红', type: 'danger', confirm: '确定冲红此费用？' }
            ]" @click="(key) => {
              if (key === 'edit') editExpense(row)
              else if (key === 'pay') openPaymentDialog(row)
              else if (key === 'reverse') handleReverse(row)
            }" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogType==='create'?'新增费用':'编辑费用'" width="500px">
      <el-form :model="expenseForm" label-width="0">
        <FormGroup title="费用信息" color="primary">
          <FormField label="日期"><el-date-picker v-model="expenseForm.expense_date" type="date" value-format="YYYY-MM-DD" style="width:100%;" /></FormField>
          <FormField label="类别"><el-input v-model="expenseForm.category" placeholder="如 办公用品" /></FormField>
          <FormField label="功能分类"><el-select v-model="expenseForm.functional_category" style="width:100%"><el-option label="管理费用" value="管理费用" /><el-option label="销售费用" value="销售费用" /><el-option label="财务费用" value="财务费用" /><el-option label="税金及附加" value="税金及附加" /></el-select></FormField>
          <FormField label="金额"><el-input v-model.number="expenseForm.amount" /></FormField>
          <FormField label="描述"><el-input v-model="expenseForm.description" type="textarea" :rows="2" /></FormField>
        </FormGroup>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" @click="saveExpense">{{ dialogType==='create'?'保存':'更新' }}</el-button></template>
    </el-dialog>

    <el-dialog v-model="paymentDialogVisible" title="费用付款" width="460px">
      <el-form :model="paymentForm" label-width="0" v-if="paymentTarget">
        <FormGroup :title="`费用 ${paymentTarget.category}, 金额 ¥${formatMoney(paymentTarget.amount)}`" color="danger">
          <FormField label="付款金额"><el-input v-model.number="paymentForm.amount" /></FormField>
          <FormField label="付款日期"><el-date-picker v-model="paymentForm.payment_date" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width:100%;" /></FormField>
          <FormField label="方式"><el-select v-model="paymentForm.payment_method" style="width:100%"><el-option label="公司账户" value="company" /><el-option label="个人垫付" value="private_advance" /></el-select></FormField>
          <FormField label="银行账户"><el-select v-model="paymentForm.bank_account_id" clearable style="width:100%" placeholder="选填"><el-option v-for="ba in bankAccounts" :key="ba.id" :label="ba.bank_name" :value="ba.id" /></el-select></FormField>
          <FormField label="描述"><el-input v-model="paymentForm.description" /></FormField>
        </FormGroup>
      </el-form>
      <template #footer><el-button @click="paymentDialogVisible=false">取消</el-button><el-button type="danger" @click="confirmPayment">确认付款</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import expensesApi from '../api/expenses'
import paymentsApi from '../api/payments'
import bankAccountsApi from '../api/bankAccounts'
import { formatMoney, formatDate } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../utils/errorHandler'
import { generateYears, isSameMonth, nowLocal } from '../utils/date'
import StatCards from '../components/StatCards.vue'
import PageHeader from '../components/PageHeader.vue'
import FilterBar from '../components/FilterBar.vue'
import FormGroup from '../components/FormGroup.vue'
import FormField from '../components/FormField.vue'
import StatusTag from '../components/StatusTag.vue'
import ActionColumn from '../components/ActionColumn.vue'

const expenses = ref([])
const loading = ref(false)
const years = ref([])
const dialogVisible = ref(false)
const filterForm = ref({ year: '' })
const dialogType = ref('create')
const currentExpenseId = ref(null)
const expenseForm = ref({ category:'', functional_category:'管理费用', amount:0, expense_date:'', description:'' })

const bankAccounts = ref([])
const paymentDialogVisible = ref(false)
const paymentTarget = ref(null)
const paymentForm = ref({ amount: 0, payment_date: '', payment_method: 'company', bank_account_id: null, description: '' })

years.value = generateYears(-2, 0)

const totalAmount = computed(() => expenses.value.reduce((s,e) => s+(Number(e.amount)||0), 0))
const monthTotal = computed(() => {
  return expenses.value.filter(e => isSameMonth(e.expense_date)).reduce((s,e) => s+(Number(e.amount)||0), 0)
})

const getExpenses = async () => {
  loading.value = true
  try {
    const params = {}
    if (filterForm.value.year) params.year = filterForm.value.year
    const r = await expensesApi.getExpenses(params)
    expenses.value = r?.items || []
  } catch (e) { handleError(e, { defaultMsg:'获取费用列表失败' }); expenses.value = [] }
  finally { loading.value = false }
}

const resetFilter = () => { filterForm.value = { year: '' }; getExpenses() }

const openCreateDialog = () => { dialogType.value='create'; currentExpenseId.value=null; expenseForm.value={category:'',functional_category:'管理费用',amount:0,expense_date:'',description:''}; dialogVisible.value=true }

const editExpense = (e) => { dialogType.value='edit'; currentExpenseId.value=e.id; expenseForm.value={category:e.category,functional_category:e.functional_category||'管理费用',amount:e.amount,expense_date:e.expense_date,description:e.description||''}; dialogVisible.value=true }

const saveExpense = async () => {
  try {
    if (dialogType.value === 'create') { await expensesApi.createExpense(expenseForm.value); ElMessage.success('创建成功') }
    else { await expensesApi.updateExpense(currentExpenseId.value, expenseForm.value); ElMessage.success('更新成功') }
    dialogVisible.value=false; getExpenses()
  } catch (e) { handleError(e, { defaultMsg:'保存失败' }) }
}

const handleReverse = async (row) => {
  try { await expensesApi.reverseExpense(row.id); ElMessage.success('费用已冲红'); getExpenses() }
  catch (e) { handleError(e, { defaultMsg:'冲红失败' }) }
}

const openPaymentDialog = async (row) => {
  paymentTarget.value = row
  paymentForm.value = {
    amount: Number(row.amount) || 0,
    payment_date: nowLocal(),
    payment_method: 'company',
    bank_account_id: null,
    description: `费用 ${row.category} 付款`
  }
  try { const r = await bankAccountsApi.getBankAccounts(); bankAccounts.value = r?.items || [] } catch (e) { bankAccounts.value = []; ElMessage.warning('银行账户列表加载失败') }
  paymentDialogVisible.value = true
}

const confirmPayment = async () => {
  try {
    await paymentsApi.createPayment({
      payment_type: 'expense', related_entity_type: 'expense',
      related_entity_id: paymentTarget.value.id,
      ...paymentForm.value
    })
    ElMessage.success('付款成功')
    paymentDialogVisible.value = false
    getExpenses()
  } catch (e) { handleError(e, { defaultMsg: '付款失败' }) }
}

useAccountAwareData(getExpenses)
</script>

<style scoped>
/* 样式已集中到 global.css */
</style>
