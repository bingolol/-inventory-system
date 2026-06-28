<template>
  <div>
    <div class="ex-stats">
      <div class="ex-stat" @click="activeCategory = ''" :class="{ 'ex-stat-active': !activeCategory }">
        <span class="ex-stat-label">全部费用</span>
        <span class="ex-stat-value c-primary">{{ formatMoney(totalAmount) }}</span>
        <span class="ex-stat-sub">{{ expenses.length }} 笔</span>
      </div>
      <div class="ex-stat" @click="activeCategory = ''">
        <span class="ex-stat-label">本月费用</span>
        <span class="ex-stat-value c-danger">{{ formatMoney(monthTotal) }}</span>
      </div>
      <div
        v-for="cat in categoryTotals"
        :key="cat.name"
        class="ex-stat ex-stat-cat"
        :class="{ 'ex-stat-active': activeCategory === cat.name }"
        :style="{ borderLeftColor: cat.color }"
        @click="filterByCategory(cat.name)"
      >
        <span class="ex-stat-label">{{ cat.name }}</span>
        <span class="ex-stat-value" :style="{ color: cat.color }">{{ formatMoney(cat.total) }}</span>
        <span class="ex-stat-sub">{{ cat.count }} 笔</span>
      </div>
    </div>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">费用管理</span>
          <el-button type="primary" @click="openCreateDialog"><el-icon><Plus /></el-icon> 新增费用</el-button>
        </div>
      </template>
      <div class="filter-bar">
        <el-select v-model="filterForm.year" placeholder="年份筛选" clearable style="width:130px">
          <el-option v-for="year in years" :key="year" :label="year" :value="year" />
        </el-select>
        <el-button type="primary" @click="getExpenses">查询</el-button>
        <el-button @click="resetFilter">重置</el-button>
      </div>
      <el-table :data="filteredExpenses" style="width:100%" v-loading="loading">
        <template #empty><el-empty description="暂无费用记录" /></template>
        <el-table-column label="日期" min-width="110">
          <template #default="{ row }">{{ formatDate(row.expense_date) }}</template>
        </el-table-column>
        <el-table-column prop="category" label="类别" min-width="100" align="center">
          <template #default="scope">
            <span class="status-badge" :class="getCategoryClass(scope.row.category)">{{ scope.row.category }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="金额" min-width="120" align="right">
          <template #default="scope"><span class="money">¥{{ formatMoney(scope.row.amount) }}</span></template>
        </el-table-column>
        <el-table-column prop="has_invoice" label="发票" min-width="70" align="center">
          <template #default="scope">
            <span class="status-badge" :class="scope.row.has_invoice ? 'success' : 'info'">{{ scope.row.has_invoice ? '有' : '无' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="payment_method" label="支付方式" min-width="110" align="center">
          <template #default="scope">
            <span class="status-badge" :class="scope.row.payment_method === 'company' ? 'primary' : 'warning'">
              {{ enumsStore.getLabel('payment_method', scope.row.payment_method) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="140" />
        <el-table-column prop="image_url" label="附件" min-width="70" align="center">
          <template #default="scope">
            <el-image v-if="scope.row.image_url" :src="resolveImageUrl(scope.row.image_url)" style="width:36px;height:36px;border-radius:6px" fit="cover" :preview-src-list="[resolveImageUrl(scope.row.image_url)]" />
            <span v-else class="c-muted">-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="130" align="center">
          <template #default="scope">
            <el-button size="small" link type="primary" @click="editExpense(scope.row)">编辑</el-button>
            <el-popconfirm title="确定删除此费用记录？" @confirm="deleteExpense(scope.row.id)">
              <template #reference><el-button size="small" link type="danger">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="dialogType === 'create' ? '新增费用' : '编辑费用'" width="560px">
      <el-form :model="expenseForm" label-width="0">
        <div class="ex-group" style="border-left-color:#4f6ef7;">
          <div class="ex-group-header"><span class="ex-group-tag" style="background:#eef1ff;color:#4f6ef7;">基本信息</span></div>
          <div class="ex-group-body">
            <div class="ex-field"><span class="ex-label" style="min-width:70px;">日期</span><el-date-picker v-model="expenseForm.expense_date" type="date" placeholder="请选择日期" value-format="YYYY-MM-DD" style="width:100%" /></div>
            <div class="ex-field"><span class="ex-label" style="min-width:70px;">类别</span><el-select v-model="expenseForm.category" placeholder="请选择类别" style="width:100%"><el-option v-for="c in categoryOptions" :key="c.value" :label="c.label" :value="c.value" /></el-select></div>
            <div class="ex-field"><span class="ex-label" style="min-width:70px;">金额</span><el-input v-model.number="expenseForm.amount" placeholder="请输入金额" /></div>
            <div class="ex-field"><span class="ex-label" style="min-width:70px;">有发票</span><el-switch v-model="expenseForm.has_invoice" /></div>
          </div>
        </div>
        <div class="ex-group" style="border-left-color:#e6a23c;">
          <div class="ex-group-header"><span class="ex-group-tag" style="background:#fdf6ec;color:#e6a23c;">支付信息</span></div>
          <div class="ex-group-body">
            <div class="ex-field"><span class="ex-label" style="min-width:70px;">支付方式</span><el-select v-model="expenseForm.payment_method" placeholder="请选择支付方式" style="width:100%"><el-option v-for="opt in enumsStore.paymentMethodOptions" :key="opt.value" :label="opt.label" :value="opt.value" /></el-select></div>
            <div class="ex-field"><span class="ex-label" style="min-width:70px;">描述</span><el-input v-model="expenseForm.description" type="textarea" placeholder="请输入描述" /></div>
            <div class="ex-field"><span class="ex-label" style="min-width:70px;">附件</span><ImageUpload v-model="expenseForm.image_url" business-type="expense" :record-id="currentExpenseId || 0" :update-api="expensesApi.updateExpense" /></div>
          </div>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveExpense">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import expensesApi from '../api/expenses'
import { formatMoney, formatDate } from '../utils/format'
import { resolveImageUrl, handleError } from '../api/index'
import ImageUpload from '../components/ImageUpload.vue'
import { useEnumsStore } from '../stores/enums'
import { useAccountAwareData } from '../composables/useAccountAwareData'

const enumsStore = useEnumsStore()
const expenses = ref([])
const loading = ref(false)
const activeCategory = ref('')

const filteredExpenses = computed(() => {
  if (!activeCategory.value) return expenses.value
  return expenses.value.filter(e => e.category === activeCategory.value)
})

const totalAmount = computed(() => {
  return filteredExpenses.value.reduce((sum, item) => sum + (Number(item.amount) || 0), 0)
})
const monthTotal = computed(() => {
  const now = new Date()
  return expenses.value
    .filter(e => {
      const d = new Date(e.expense_date)
      return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear()
    })
    .reduce((s, e) => s + (Number(e.amount) || 0), 0)
})

const filterForm = ref({ category: '', year: '' })
const years = ref([])

const CATEGORY_COLORS = {
  '房租': '#4f6ef7', '水电': '#67c23a', '工资': '#e6a23c', '材料': '#f56c6c',
  '办公用品': '#909399', '运费': '#4f6ef7', '维修': '#e6a23c', '其他': '#909399'
}
const categoryTotals = computed(() => {
  const map = {}
  for (const e of expenses.value) {
    if (!map[e.category]) map[e.category] = { name: e.category, total: 0, count: 0, color: CATEGORY_COLORS[e.category] || '#909399' }
    map[e.category].total += Number(e.amount || 0)
    map[e.category].count++
  }
  return Object.values(map).sort((a, b) => b.total - a.total)
})

const filterByCategory = (name) => {
  activeCategory.value = activeCategory.value === name ? '' : name
}
const dialogVisible = ref(false)
const dialogType = ref('create')
const currentExpenseId = ref(null)
const expenseForm = ref({ category: '', amount: 0, expense_date: '', has_invoice: false, payment_method: 'company', description: '', image_url: '' })

const categoryOptions = computed(() => enumsStore.expenseCategoryOptions)

const generateYears = () => {
  const currentYear = new Date().getFullYear()
  for (let i = currentYear - 2; i <= currentYear + 2; i++) years.value.push(i)
}

const getExpenses = async () => {
  loading.value = true
  try {
    const params = {}
    for (const [key, value] of Object.entries(filterForm.value)) {
      if (value !== '' && value !== null && value !== undefined) params[key] = value
    }
    const response = await expensesApi.getExpenses(params)
    expenses.value = response?.items || []
  } catch (error) {
    handleError(error, { defaultMsg: '获取费用列表失败，请检查网络连接' })
    expenses.value = []
  } finally {
    loading.value = false
  }
}

const resetFilter = () => {
  filterForm.value = { category: '', year: '' }
  activeCategory.value = ''
  getExpenses()
}

const openCreateDialog = () => {
  dialogType.value = 'create'
  currentExpenseId.value = null
  expenseForm.value = { category: '', amount: 0, expense_date: '', has_invoice: false, payment_method: 'company', description: '', image_url: '' }
  dialogVisible.value = true
}

const saveExpense = async () => {
  try {
    if (dialogType.value === 'create') {
      await expensesApi.createExpense(expenseForm.value)
      ElMessage.success('费用创建成功')
    } else {
      await expensesApi.updateExpense(currentExpenseId.value, expenseForm.value)
      ElMessage.success('费用更新成功')
    }
    dialogVisible.value = false
    getExpenses()
  } catch (error) {
    handleError(error, { defaultMsg: '保存费用失败，请检查输入数据是否正确' })
  }
}

const editExpense = (expense) => {
  dialogType.value = 'edit'
  currentExpenseId.value = expense.id
  expenseForm.value = { ...expense }
  dialogVisible.value = true
}

const deleteExpense = async (id) => {
  try {
    await expensesApi.deleteExpense(id)
    ElMessage.success('费用已删除')
    getExpenses()
  } catch (error) {
    handleError(error, { defaultMsg: '删除费用失败，请检查该费用是否被其他单据引用' })
  }
}

const CATEGORY_CLASS_MAP = {
  '房租': 'primary',
  '水电': 'info',
  '工资': 'success',
  '材料': 'warning',
  '办公用品': 'info',
  '运费': 'primary',
  '维修': 'warning',
  '其他': 'info'
}
const getCategoryClass = (category) => CATEGORY_CLASS_MAP[category] || ''

generateYears()
useAccountAwareData(getExpenses)
enumsStore.fetchEnums()
</script>

<style scoped>
.exp-total-bar {
  margin-top: 12px;
  padding: 10px 16px;
  background: #fafafa;
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
  color: #86909c;
}
.exp-total-amount {
  color: #f56c6c;
  font-weight: 600;
  font-family: 'Consolas', 'Monaco', monospace;
}
.ex-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}
.ex-stat {
  flex: 1;
  min-width: 140px;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-left: 4px solid #4f6ef7;
  border-radius: 12px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}
.ex-stat:hover { transform: translateY(-2px); box-shadow: 0 4px 12px rgba(0,0,0,0.06); }
.ex-stat-active { background: #f4f6ff; border-color: #4f6ef7; box-shadow: 0 2px 8px rgba(79,110,247,0.12); }
.ex-stat-cat { border-left-color: #909399; }
.ex-stat-label { font-size: 12px; color: #86909c; font-weight: 500; letter-spacing: 0.5px; }
.ex-stat-value { font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }
.ex-stat-sub { font-size: 12px; color: #c9cdd4; }
.ex-group { background: #fafafa; border: 1px solid #f0f0f0; border-left: 4px solid; border-radius: 12px; overflow: hidden; margin-bottom: 16px; }
.ex-group-header { padding: 12px 16px 4px; }
.ex-group-tag { display: inline-block; padding: 2px 12px; border-radius: 9999px; font-size: 12px; font-weight: 600; letter-spacing: 0.5px; }
.ex-group-body { padding: 4px 16px 12px; display: flex; flex-direction: column; gap: 10px; }
.ex-field { display: flex; align-items: center; gap: 12px; }
.ex-label { font-size: 13px; color: #4e5969; flex-shrink: 0; }
</style>
