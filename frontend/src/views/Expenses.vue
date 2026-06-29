<template>
  <div>
    <div class="row">
      <div class="c4"><div class="stat-mini"><span class="stat-mini-label">本月费用</span><span class="stat-mini-value" style="color:var(--danger);">{{ formatMoney(monthTotal) }}</span></div></div>
      <div class="c4"><div class="stat-mini"><span class="stat-mini-label">筛选合计</span><span class="stat-mini-value" style="color:var(--primary);">{{ formatMoney(totalAmount) }}</span></div></div>
      <div class="c4"><div class="stat-mini"><span class="stat-mini-label">记录数</span><span class="stat-mini-value" style="color:var(--success);">{{ expenses.length }} 笔</span></div></div>
    </div>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">费用管理</span>
          <div class="card-header-actions">
            <el-button type="primary" @click="openCreateDialog">
              <el-icon><Plus /></el-icon> 新增费用
            </el-button>
          </div>
        </div>
      </template>
      <div class="filter-bar" style="margin-bottom:12px;">
        <el-select v-model="filterForm.year" placeholder="年份" clearable style="width:120px;">
          <el-option v-for="y in years" :key="y" :label="y" :value="y" />
        </el-select>
        <el-button type="primary" @click="getExpenses">查询</el-button>
        <el-button @click="resetFilter">重置</el-button>
      </div>
      <el-table :data="expenses" stripe style="width:100%" v-loading="loading">
        <template #empty>
          <el-empty description="暂无费用记录" />
        </template>
        <el-table-column prop="expense_date" label="日期" min-width="110">
          <template #default="{ row }">{{ formatDate(row.expense_date) }}</template>
        </el-table-column>
        <el-table-column label="类别" min-width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ row.category }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="金额" min-width="120" align="right">
          <template #default="{ row }">
            <span class="money" style="color:var(--danger);">-{{ formatMoney(row.amount) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200">
          <template #default="{ row }">{{ row.description || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="130" align="center">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="editExpense(row)">编辑</el-button>
            <el-popconfirm title="确定删除？" @confirm="deleteExpense(row.id)">
              <template #reference>
                <el-button size="small" link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogType==='create'?'新增费用':'编辑费用'" width="500px">
      <el-form :model="expenseForm" label-width="0">
        <div class="fg" style="border-left-color:var(--primary);">
          <div class="fgh"><span class="fgt" style="background:var(--primary-light);color:var(--primary);">费用信息</span></div>
          <div class="fgb">
            <div class="ff"><span class="fl" style="min-width:70px;">日期</span><el-date-picker v-model="expenseForm.expense_date" type="date" value-format="YYYY-MM-DD" style="width:100%;" /></div>
            <div class="ff"><span class="fl" style="min-width:70px;">类别</span><el-input v-model="expenseForm.category" placeholder="如 办公用品" /></div>
            <div class="ff"><span class="fl" style="min-width:70px;">金额</span><el-input v-model.number="expenseForm.amount" /></div>
            <div class="ff"><span class="fl" style="min-width:70px;">描述</span><el-input v-model="expenseForm.description" type="textarea" :rows="2" /></div>
          </div>
        </div>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" @click="saveExpense">{{ dialogType==='create'?'保存':'更新' }}</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import expensesApi from '../api/expenses'
import { formatMoney, formatDate } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../utils/errorHandler'

const expenses = ref([])
const loading = ref(false)
const filterForm = ref({ year: '' })
const years = ref([])
const dialogVisible = ref(false)
const dialogType = ref('create')
const currentExpenseId = ref(null)
const expenseForm = ref({ category:'', amount:0, expense_date:'', description:'' })

for (let i = new Date().getFullYear()-2; i <= new Date().getFullYear(); i++) years.value.push(i)

const totalAmount = computed(() => expenses.value.reduce((s,e) => s+(Number(e.amount)||0), 0))
const monthTotal = computed(() => {
  const n = new Date()
  return expenses.value.filter(e => { if (!e.expense_date) return false; const d = new Date(e.expense_date); return !isNaN(d.getTime()) && d.getMonth()===n.getMonth() && d.getFullYear()===n.getFullYear() }).reduce((s,e) => s+(Number(e.amount)||0), 0)
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

const openCreateDialog = () => { dialogType.value='create'; currentExpenseId.value=null; expenseForm.value={category:'',amount:0,expense_date:'',description:''}; dialogVisible.value=true }

const editExpense = (e) => { dialogType.value='edit'; currentExpenseId.value=e.id; expenseForm.value={category:e.category,amount:e.amount,expense_date:e.expense_date,description:e.description||''}; dialogVisible.value=true }

const saveExpense = async () => {
  try {
    if (dialogType.value === 'create') { await expensesApi.createExpense(expenseForm.value); ElMessage.success('创建成功') }
    else { await expensesApi.updateExpense(currentExpenseId.value, expenseForm.value); ElMessage.success('更新成功') }
    dialogVisible.value=false; getExpenses()
  } catch (e) { handleError(e, { defaultMsg:'保存失败' }) }
}

const deleteExpense = async (id) => {
  try { await expensesApi.deleteExpense(id); ElMessage.success('已删除'); getExpenses() }
  catch (e) { handleError(e, { defaultMsg:'删除失败' }) }
}

useAccountAwareData(getExpenses)
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
