<template>
  <div class="expenses-container">
    <el-card shadow="never">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="font-weight:600;">费用管理</span>
          <el-button type="primary" @click="dialogVisible = true"><el-icon><Plus /></el-icon> 新增费用</el-button>
        </div>
      </template>
    
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

    <!-- 费用列表 -->
    <el-table :data="expenses" style="width: 100%" v-loading="loading">
      <template #empty>
        <el-empty description="暂无费用记录" />
      </template>
      <el-table-column prop="expense_date" label="日期" width="120" />
      <el-table-column prop="category" label="类别" width="100" align="center">
        <template #default="scope">
          <el-tag :type="getCategoryType(scope.row.category)">
            {{ scope.row.category }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="amount" label="金额" width="120" align="right">
        <template #default="scope">
          <span class="money">¥{{ formatMoney(scope.row.amount) }}</span>
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
            {{ enumsStore.getLabel('payment_method', scope.row.payment_method) }}
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
          <el-popconfirm title="确定删除此费用记录？" @confirm="deleteExpense(scope.row.id)">
            <template #reference>
              <el-button type="danger" size="small">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 筛选合计 -->
    <div style="margin-top:12px;padding:10px 16px;background:var(--fill-light);border-radius:6px;display:flex;justify-content:space-between;align-items:center;">
      <div style="display:flex;gap:24px;font-size:14px;">
        <span>筛选合计：</span>
        <span style="color:var(--danger);font-weight:600;">金额 ¥{{ formatMoney(totalAmount) }}</span>
      </div>
    </div>
    </el-card>

    <!-- 新增/编辑弹窗 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogType === 'create' ? '新增费用' : '编辑费用'"
      width="500px"
    >
      <el-form :model="expenseForm" label-width="100px">
        <el-form-item label="日期" required>
          <el-date-picker v-model="expenseForm.expense_date" type="date" placeholder="请选择日期" value-format="YYYY-MM-DD" style="width: 100%" />
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
            <el-option v-for="opt in enumsStore.paymentMethodOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="expenseForm.description" type="textarea" placeholder="请输入描述" />
        </el-form-item>
        <el-form-item label="附件图片">
          <ImageUpload v-model="expenseForm.image_url" business-type="expense" :record-id="currentExpenseId || 0" :update-api="expensesApi.updateExpense" />
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
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { useAccountStore } from '../stores/account'
const accountStore = useAccountStore()
import expensesApi from '../api/expenses'
import commonApi, { formatMoney } from '../api/common'
import { resolveImageUrl } from '../api/index'
import ImageUpload from '../components/ImageUpload.vue'
import { useEnumsStore } from '../stores/enums'
import { useAccountAwareData } from '../composables/useAccountAwareData'

const enumsStore = useEnumsStore()

// 费用列表
const expenses = ref([])
const loading = ref(false)

// 计算当前列表的金额总和
const totalAmount = computed(() => {
  return expenses.value.reduce((sum, item) => sum + (Number(item.amount) || 0), 0)
})

// 筛选表单
const filterForm = ref({
  category: '',
  year: ''
})
// 年份列表
const years = ref([])

// 弹窗相关
const dialogVisible = ref(false)
const dialogType = ref('create')
const currentExpenseId = ref(null)
const expenseForm = ref({
  category: '',
  amount: 0,
  expense_date: '',
  has_invoice: false,
  payment_method: 'company',
  description: '',
  image_url: ''
})

// 费用类别选项（从Pinia枚举store获取，支持allow-create自由输入）
const categoryOptions = computed(() => enumsStore.expenseCategoryOptions)

// 生成年份列表
const generateYears = () => {
  const currentYear = new Date().getFullYear()
  for (let i = currentYear - 2; i <= currentYear + 2; i++) {
    years.value.push(i)
  }
}

// 获取费用列表
const getExpenses = async () => {
  loading.value = true
  try {
    // 过滤空字符串参数，避免 422 错误
    const params = {}
    for (const [key, value] of Object.entries(filterForm.value)) {
      if (value !== '' && value !== null && value !== undefined) {
        params[key] = value
      }
    }
    const response = await expensesApi.getExpenses(params)
    expenses.value = response?.items || []
  } catch (error) {
    console.error('获取费用列表失败:', error)
    expenses.value = []
  } finally {
    loading.value = false
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
      await expensesApi.createExpense(expenseForm.value)
      ElMessage.success('费用创建成功')
    } else {
      await expensesApi.updateExpense(currentExpenseId.value, expenseForm.value)
      ElMessage.success('费用更新成功')
    }
    dialogVisible.value = false
    getExpenses()
  } catch (error) {
    console.error('保存费用失败:', error)
    ElMessage.error(error.response?.data?.detail || '保存费用失败')
  }
}

// 编辑费用
const editExpense = (expense) => {
  dialogType.value = 'edit'
  currentExpenseId.value = expense.id
  expenseForm.value = {
    ...expense
  }
  dialogVisible.value = true
}

// 删除费用
const deleteExpense = async (id) => {
  try {
    await expensesApi.deleteExpense(id)
    ElMessage.success('费用已删除')
    getExpenses()
  } catch (error) {
    console.error('删除费用失败:', error)
    ElMessage.error('删除费用失败')
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

generateYears()
useAccountAwareData(getExpenses)
enumsStore.fetchEnums()
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
