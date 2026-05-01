<template>
  <div class="expenses-container">
    <h2>费用管理</h2>
    
    <!-- 筛选条件 -->
    <el-form :inline="true" :model="filterForm" class="filter-form">
      <el-form-item label="类别">
        <el-select v-model="filterForm.category" placeholder="全部">
          <el-option v-for="category in categoryOptions" :key="category.value" :label="category.label" :value="category.value" />
        </el-select>
      </el-form-item>
      <el-form-item label="年份">
        <el-select v-model="filterForm.year" placeholder="全部">
          <el-option v-for="year in years" :key="year" :label="year" :value="year" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="getExpenses">查询</el-button>
        <el-button @click="resetFilter">重置</el-button>
      </el-form-item>
    </el-form>

    <!-- 操作按钮 -->
    <el-button type="primary" @click="dialogVisible = true">新增费用</el-button>

    <!-- 费用列表 -->
    <el-table :data="expenses" style="width: 100%">
      <el-table-column prop="expense_date" label="日期" width="120" />
      <el-table-column prop="project_name" label="项目" width="150" />
      <el-table-column prop="category" label="类别" width="100" align="center">
        <template #default="scope">
          <el-tag :type="getCategoryType(scope.row.category)">
            {{ scope.row.category }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="amount" label="金额" width="120" align="right">
        <template #default="scope">
          {{ scope.row.amount.toFixed(2) }}
        </template>
      </el-table-column>
      <el-table-column prop="has_invoice" label="有发票" width="100" align="center">
        <template #default="scope">
          <el-tag :type="scope.row.has_invoice ? 'success' : 'info'">
            {{ scope.row.has_invoice ? '是' : '否' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="payment_method" label="支付方式" width="120" align="center">
        <template #default="scope">
          <el-tag :type="scope.row.payment_method === 'company' ? 'primary' : 'warning'">
            {{ scope.row.payment_method === 'company' ? '公司' : '个人垫付' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="description" label="描述" />
      <el-table-column prop="image_url" label="附件" width="80" align="center">
        <template #default="scope">
          <el-image v-if="scope.row.image_url" :src="resolveImageUrl(scope.row.image_url)" style="width:40px;height:40px;" fit="cover" :preview-src-list="[resolveImageUrl(scope.row.image_url)]" />
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" align="center">
        <template #default="scope">
          <el-button @click="editExpense(scope.row)" type="primary" size="small">
            编辑
          </el-button>
          <el-button @click="deleteExpense(scope.row.id)" type="danger" size="small">
            删除
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'create' ? '新增费用' : '编辑费用'"
      width="500px"
    >
      <el-form :model="expenseForm" label-width="100px">
        <el-form-item label="日期" required>
          <el-date-picker v-model="expenseForm.expense_date" type="date" placeholder="请选择日期" style="width: 100%" />
        </el-form-item>
        <el-form-item label="项目">
          <el-select v-model="expenseForm.project_name" placeholder="请选择项目" allow-create filterable>
            <el-option v-for="project in projects" :key="project" :label="project" :value="project" />
          </el-select>
        </el-form-item>
        <el-form-item label="类别" required>
          <el-select v-model="expenseForm.category" placeholder="请选择类别">
            <el-option v-for="category in categoryOptions" :key="category.value" :label="category.label" :value="category.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="金额" required>
          <el-input v-model.number="expenseForm.amount" placeholder="请输入金额" />
        </el-form-item>
        <el-form-item label="有发票">
          <el-switch v-model="expenseForm.has_invoice" />
        </el-form-item>
        <el-form-item label="支付方式" required>
          <el-select v-model="expenseForm.payment_method" placeholder="请选择支付方式">
            <el-option label="公司" value="company" />
            <el-option label="个人垫付" value="private_advance" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="expenseForm.description" type="textarea" placeholder="请输入描述" />
        </el-form-item>
        <el-form-item label="附件图片">
          <ImageUpload v-model="expenseForm.image_url" business-type="expense" :record-id="currentExpenseId || 0" :update-api="api.updateExpense" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveExpense">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { accountStore } from '../stores/account'
import api from '../api'
import { resolveImageUrl } from '../api'
import ImageUpload from '../components/ImageUpload.vue'

// 费用列表
const expenses = ref([])
// 筛选表单
const filterForm = ref({
  category: '',
  year: ''
})
// 年份列表
const years = ref([])
// 项目列表
const projects = ref([])

// 弹窗相关
const dialogVisible = ref(false)
const dialogType = ref('create')
const currentExpenseId = ref(null)
const expenseForm = ref({
  project_name: '',
  category: '',
  amount: 0,
  expense_date: '',
  has_invoice: false,
  payment_method: 'company',
  description: '',
  image_url: ''
})

// 费用类别选项（从API获取，支持allow-create自由输入）
const categoryOptions = ref([])

const loadEnums = async () => {
  try {
    const enums = await api.getEnums()
    categoryOptions.value = enums.expense_categories.map(c => ({ label: c, value: c }))
  } catch (e) { /* 降级：保留空列表 */ }
}

// 生成年份列表
const generateYears = () => {
  const currentYear = new Date().getFullYear()
  for (let i = currentYear - 2; i <= currentYear + 2; i++) {
    years.value.push(i)
  }
}

// 获取费用列表
const getExpenses = async () => {
  try {
    // 过滤空字符串参数，避免 422 错误
    const params = {}
    for (const [key, value] of Object.entries(filterForm.value)) {
      if (value !== '' && value !== null && value !== undefined) {
        params[key] = value
      }
    }
    const response = await api.getExpenses(params)
    expenses.value = response?.items || []
  } catch (error) {
    console.error('获取费用列表失败:', error)
    expenses.value = []
  }
}

// 重置筛选
const resetFilter = () => {
  filterForm.value = {
    category: '',
    year: ''
  }
  getExpenses()
}

// 保存费用
const saveExpense = async () => {
  try {
    if (dialogType.value === 'create') {
      await api.createExpense(expenseForm.value)
    } else {
      await api.updateExpense(currentExpenseId.value, expenseForm.value)
    }
    dialogVisible.value = false
    getExpenses()
  } catch (error) {
    console.error('保存费用失败:', error)
  }
}

// 编辑费用
const editExpense = (expense) => {
  dialogType.value = 'edit'
  currentExpenseId.value = expense.id
  expenseForm.value = {
    ...expense,
    expense_date: expense.expense_date ? new Date(expense.expense_date) : ''
  }
  dialogVisible.value = true
}

// 删除费用
const deleteExpense = async (id) => {
  try {
    await api.deleteExpense(id)
    getExpenses()
  } catch (error) {
    console.error('删除费用失败:', error)
  }
}

// 获取类别类型
const getCategoryType = (category) => {
  switch (category) {
    case '房租':
      return 'primary'
    case '水电':
      return 'info'
    case '工资':
      return 'success'
    case '材料':
      return 'warning'
    case '办公用品':
      return ''
    case '运费':
      return 'primary'
    case '维修':
      return 'warning'
    case '其他':
      return 'danger'
    default:
      return 'default'
  }
}

onMounted(() => {
  generateYears()
  getExpenses()
  loadEnums()
  // 获取项目列表
  api.getProjects().then(response => {
    projects.value = response?.items ? response.items.map(item => item.project_name) : []
  })
})
</script>

<style scoped>
.expenses-container {
  padding: 20px;
}

.filter-form {
  margin-bottom: 20px;
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}
</style>
