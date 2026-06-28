<template>
  <div>
    <div class="row" style="margin-bottom:16px;">
      <div class="c4"><div class="c"><div class="cl">本月费用</div><div class="cv c-danger">{{ formatMoney(monthTotal) }}</div></div></div>
      <div class="c4"><div class="c"><div class="cl">筛选合计</div><div class="cv c-primary">{{ formatMoney(totalAmount) }}</div></div></div>
      <div class="c4"><div class="c"><div class="cl">记录数</div><div class="cv c-success">{{ expenses.length }} 笔</div></div></div>
    </div>

    <div class="box">
      <div class="bh"><span class="bt">费用管理</span><el-button size="small" @click="openCreateDialog">+ 新增费用</el-button></div>
      <div class="filter-bar" style="margin-bottom:12px;">
        <el-select v-model="filterForm.year" placeholder="年份" clearable style="width:120px;">
          <el-option v-for="y in years" :key="y" :label="y" :value="y" />
        </el-select>
        <el-button size="small" type="primary" @click="getExpenses">查询</el-button>
        <el-button size="small" @click="resetFilter">重置</el-button>
      </div>
      <table class="tbl" v-if="expenses.length">
        <tr><th>日期</th><th>类别</th><th style="width:120px;">金额</th><th>描述</th><th style="width:90px;">操作</th></tr>
        <tr v-for="e in expenses" :key="e.id">
          <td>{{ formatDate(e.expense_date) }}</td>
          <td><span class="bg bi">{{ e.category }}</span></td>
          <td class="c-danger" style="font-weight:600;">-{{ formatMoney(e.amount) }}</td>
          <td style="color:#86909c;">{{ e.description || '-' }}</td>
          <td>
            <el-button size="small" link type="primary" @click="editExpense(e)">编辑</el-button>
            <el-popconfirm title="确定删除？" @confirm="deleteExpense(e.id)"><template #reference><el-button size="small" link type="danger">删除</el-button></template></el-popconfirm>
          </td>
        </tr>
      </table>
      <div v-else style="padding:24px 0;text-align:center;color:#c9cdd4;font-size:13px;">暂无费用记录</div>
    </div>

    <el-dialog v-model="dialogVisible" :title="dialogType==='create'?'新增费用':'编辑费用'" width="500px">
      <el-form :model="expenseForm" label-width="0">
        <div class="fg" style="border-left-color:#4f62c0;">
          <div class="fgh"><span class="fgt" style="background:#eef1ff;color:#4f62c0;">费用信息</span></div>
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
  return expenses.value.filter(e => { const d = new Date(e.expense_date); return d.getMonth()===n.getMonth() && d.getFullYear()===n.getFullYear() }).reduce((s,e) => s+(Number(e.amount)||0), 0)
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
.row { display:flex; gap:12px; margin-bottom:16px; }
.c4 { flex:1; }
.c { background:#fff; border:1px solid #edf0f5; border-radius:10px; padding:14px 16px; }
.cl { font-size:12px; color:#4e5969; font-weight:500; margin-bottom:4px; }
.cv { font-size:24px; font-weight:700; letter-spacing:-0.5px; }

.box { background:#fff; border:1px solid #edf0f5; border-radius:10px; padding:16px; }
.bh { display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }
.bt { font-size:13px; font-weight:600; color:#1d2129; }

.tbl { width:100%; border-collapse:collapse; }
.tbl th { text-align:left; padding:8px 10px; font-size:11px; font-weight:600; color:#86909c; border-bottom:1px solid #f5f6f8; }
.tbl td { padding:8px 10px; font-size:13px; color:#4e5969; border-bottom:1px solid #f8f9fa; }
.tbl tr:last-child td { border:none; }

.bg { display:inline-block; padding:1px 8px; border-radius:4px; font-size:11px; font-weight:500; }
.bi { background:#f5f6f8; color:#4e5969; }

.fg { background:#fafafa; border:1px solid #f0f0f0; border-left:4px solid; border-radius:12px; overflow:hidden; }
.fgh { padding:12px 16px 4px; }
.fgt { display:inline-block; padding:2px 12px; border-radius:9999px; font-size:12px; font-weight:600; }
.fgb { padding:4px 16px 12px; display:flex; flex-direction:column; gap:10px; }
.ff { display:flex; align-items:center; gap:12px; }
.fl { font-size:13px; color:#4e5969; flex-shrink:0; }

.c-primary { color:#4f62c0; }
.c-danger { color:#f56c6c; }
.c-success { color:#67c23a; }
</style>
