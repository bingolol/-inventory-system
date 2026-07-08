<template>
  <div>
    <StatCards :items="[
      { label: '本月收款', value: formatMoney(monthTotal), color: 'success' },
      { label: '筛选合计', value: formatMoney(totalAmount), color: 'primary' },
      { label: '记录数', value: receipts.length + ' 笔', color: 'success' }
    ]" />

    <el-card shadow="never">
      <template #header>
        <PageHeader title="收款管理">
          <template #actions>
            <el-button type="primary" @click="openCreateDialog"><el-icon><Plus /></el-icon> 新增收款</el-button>
          </template>
        </PageHeader>
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
          <template #default="{ row }"><StatusTag :status="row.receipt_method" type="receipt_method" /></template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column prop="created_at" label="创建时间" min-width="130">
          <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <ActionColumn :actions="[
              { key: 'reverse', label: '冲红', type: 'danger', confirm: '确定冲红此收款？' }
            ]" @click="(key) => key === 'reverse' && handleReverse(row)" />
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" title="新增收款" width="500px">
      <el-form :model="receiptForm" label-width="0">
        <FormGroup title="收款信息" color="success">
          <FormField label="收款日期" label-width="80px"><el-date-picker v-model="receiptForm.receipt_date" type="date" value-format="YYYY-MM-DDTHH:mm:ss" style="width:100%;" /></FormField>
          <FormField label="收款金额" label-width="80px"><el-input v-model.number="receiptForm.amount" /></FormField>
          <FormField label="收款类型" label-width="80px"><el-select v-model="receiptForm.receipt_type" style="width:100%"><el-option label="销售收款" value="sale" /></el-select></FormField>
          <FormField label="关联类型" label-width="80px"><el-select v-model="receiptForm.related_entity_type" style="width:100%"><el-option label="销售单" value="sale_order" /></el-select></FormField>
          <FormField label="关联单号" label-width="80px"><el-select v-model="receiptForm.related_entity_id" filterable style="width:100%" placeholder="选择销售单"><el-option v-for="so in saleOrders" :key="so.id" :label="`${so.order_no} - ¥${so.total_price}`" :value="so.id" /></el-select></FormField>
          <FormField label="收款方式" label-width="80px"><el-select v-model="receiptForm.receipt_method" style="width:100%"><el-option label="公司账户" value="company" /><el-option label="个人垫付" value="private_advance" /></el-select></FormField>
          <FormField label="银行账户" label-width="80px"><el-select v-model="receiptForm.bank_account_id" clearable style="width:100%" placeholder="选择银行账户（可选）"><el-option v-for="ba in bankAccounts" :key="ba.id" :label="ba.bank_name" :value="ba.id" /></el-select></FormField>
          <FormField label="描述" label-width="80px"><el-input v-model="receiptForm.description" /></FormField>
        </FormGroup>
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
import { nowLocal, isSameMonth } from '../utils/date'
import StatCards from '../components/StatCards.vue'
import PageHeader from '../components/PageHeader.vue'
import FormGroup from '../components/FormGroup.vue'
import FormField from '../components/FormField.vue'
import StatusTag from '../components/StatusTag.vue'
import ActionColumn from '../components/ActionColumn.vue'

const receipts = ref([])
const saleOrders = ref([])
const bankAccounts = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const receiptForm = ref({
  receipt_type: 'sale', related_entity_type: 'sale_order', related_entity_id: null,
  amount: 0, receipt_method: 'company', receipt_date: nowLocal(),
  bank_account_id: null, description: ''
})

const totalAmount = computed(() => receipts.value.reduce((s, e) => s + (Number(e.amount) || 0), 0))
const monthTotal = computed(() => {
  return receipts.value.filter(e => isSameMonth(e.receipt_date)).reduce((s,e) => s+(Number(e.amount)||0), 0)
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
    amount: 0, receipt_method: 'company', receipt_date: nowLocal(),
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
/* 样式已集中到 global.css */
</style>
