<template>
  <div class="opening-balance-container">
    <h2>期初余额设置</h2>
    
    <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="期初日期" prop="date">
            <el-date-picker v-model="form.date" type="date" placeholder="选择日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" />
          </el-form-item>
        </el-col>
      </el-row>
      
      <el-divider>资产类</el-divider>
      <el-row :gutter="20">
        <el-col :span="8">
          <el-form-item label="现金余额" prop="cash_balance">
            <el-input-number v-model="form.cash_balance" :precision="2" :min="0" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="银行存款" prop="bank_balance">
            <el-input-number v-model="form.bank_balance" :precision="2" :min="0" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="应收账款" prop="accounts_receivable">
            <el-input-number v-model="form.accounts_receivable" :precision="2" :min="0" style="width: 100%" />
          </el-form-item>
        </el-col>
      </el-row>
      
      <el-row :gutter="20">
        <el-col :span="8">
          <el-form-item label="库存价值" prop="inventory_value">
            <el-input-number v-model="form.inventory_value" :precision="2" :min="0" style="width: 100%" />
          </el-form-item>
        </el-col>
      </el-row>
      
      <el-divider>负债类</el-divider>
      <el-row :gutter="20">
        <el-col :span="8">
          <el-form-item label="应付账款" prop="accounts_payable">
            <el-input-number v-model="form.accounts_payable" :precision="2" :min="0" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="应交税费" prop="tax_payable">
            <el-input-number v-model="form.tax_payable" :precision="2" :min="0" style="width: 100%" />
          </el-form-item>
        </el-col>
      </el-row>
      
      <el-divider>权益类</el-divider>
      <el-row :gutter="20">
        <el-col :span="8">
          <el-form-item label="未分配利润" prop="retained_earnings">
            <el-input-number v-model="form.retained_earnings" :precision="2" style="width: 100%" />
          </el-form-item>
        </el-col>
      </el-row>
      
      <el-divider>平衡检查</el-divider>
      <el-row>
        <el-col :span="24">
          <el-alert :title="balanceStatus" :type="isBalanced ? 'success' : 'error'" show-icon />
        </el-col>
      </el-row>
      
      <el-form-item>
        <el-button type="primary" @click="submitForm" :loading="loading">保存期初余额</el-button>
        <el-button @click="resetForm">重置</el-button>
        <el-button @click="loadLatest" v-if="!isNew">加载最新</el-button>
      </el-form-item>
    </el-form>
    
    <!-- 期初余额历史记录 -->
    <el-card class="history-card" v-if="openingBalances.length > 0">
      <template #header>
        <span>期初余额历史记录</span>
      </template>
      <el-table :data="openingBalances" style="width: 100%">
        <el-table-column prop="date" label="日期" width="120">
          <template #default="scope">
            {{ formatDate(scope.row.date) }}
          </template>
        </el-table-column>
        <el-table-column prop="cash_balance" label="现金" width="100" align="right">
          <template #default="scope">
            {{ scope.row.cash_balance.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="bank_balance" label="银行存款" width="100" align="right">
          <template #default="scope">
            {{ scope.row.bank_balance.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="accounts_receivable" label="应收账款" width="100" align="right">
          <template #default="scope">
            {{ scope.row.accounts_receivable.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="inventory_value" label="库存" width="100" align="right">
          <template #default="scope">
            {{ scope.row.inventory_value.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="accounts_payable" label="应付账款" width="100" align="right">
          <template #default="scope">
            {{ scope.row.accounts_payable.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="tax_payable" label="应交税费" width="100" align="right">
          <template #default="scope">
            {{ scope.row.tax_payable.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column prop="retained_earnings" label="未分配利润" width="100" align="right">
          <template #default="scope">
            {{ scope.row.retained_earnings.toFixed(2) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center">
          <template #default="scope">
            <el-button size="small" @click="editOpeningBalance(scope.row)">编辑</el-button>
            <el-button size="small" type="danger" @click="deleteOpeningBalance(scope.row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import api from '../api'

const formRef = ref()
const loading = ref(false)
const openingBalances = ref([])
const isNew = ref(true)
const currentId = ref(null)

const form = ref({
  date: new Date().toISOString().split('T')[0],
  cash_balance: 0,
  bank_balance: 0,
  accounts_receivable: 0,
  inventory_value: 0,
  accounts_payable: 0,
  tax_payable: 0,
  retained_earnings: 0
})

const rules = {
  date: [
    { required: true, message: '请选择期初日期', trigger: 'blur' }
  ]
}

// 计算资产负债表平衡
const isBalanced = computed(() => {
  const totalAssets = form.value.cash_balance + form.value.bank_balance + form.value.accounts_receivable + form.value.inventory_value
  const totalLiabilities = form.value.accounts_payable + form.value.tax_payable
  const totalEquity = form.value.retained_earnings
  return Math.abs(totalAssets - (totalLiabilities + totalEquity)) < 0.01
})

const balanceStatus = computed(() => {
  const totalAssets = form.value.cash_balance + form.value.bank_balance + form.value.accounts_receivable + form.value.inventory_value
  const totalLiabilities = form.value.accounts_payable + form.value.tax_payable
  const totalEquity = form.value.retained_earnings
  const difference = totalAssets - (totalLiabilities + totalEquity)
  
  if (Math.abs(difference) < 0.01) {
    return `资产负债表平衡 ✓ (资产: ${totalAssets.toFixed(2)} = 负债: ${totalLiabilities.toFixed(2)} + 权益: ${totalEquity.toFixed(2)})`
  } else {
    return `资产负债表不平衡 ✗ (差额: ${difference.toFixed(2)})`
  }
})

const formatDate = (dateStr) => {
  return new Date(dateStr).toLocaleDateString('zh-CN')
}

const loadOpeningBalances = async () => {
  try {
    const response = await api.getOpeningBalances()
    openingBalances.value = response
  } catch (error) {
    ElMessage.error('加载期初余额失败')
  }
}

const submitForm = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      if (!isBalanced.value) {
        ElMessage.error('资产负债表不平衡，请检查数据')
        return
      }
      
      loading.value = true
      try {
        if (isNew.value) {
          await api.createOpeningBalance(form.value)
          ElMessage.success('期初余额创建成功')
        } else {
          await api.updateOpeningBalance(currentId.value, form.value)
          ElMessage.success('期初余额更新成功')
        }
        resetForm()
        loadOpeningBalances()
      } catch (error) {
        ElMessage.error(error.response?.data?.detail || '操作失败')
      } finally {
        loading.value = false
      }
    }
  })
}

const resetForm = () => {
  form.value = {
    date: new Date().toISOString().split('T')[0],
    cash_balance: 0,
    bank_balance: 0,
    accounts_receivable: 0,
    inventory_value: 0,
    accounts_payable: 0,
    tax_payable: 0,
    retained_earnings: 0
  }
  isNew.value = true
  currentId.value = null
}

const editOpeningBalance = (row) => {
  form.value = { ...row }
  isNew.value = false
  currentId.value = row.id
}

const deleteOpeningBalance = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这条期初余额记录吗？', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await api.deleteOpeningBalance(id)
    ElMessage.success('删除成功')
    loadOpeningBalances()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

const loadLatest = async () => {
  try {
    const response = await api.getLatestOpeningBalance()
    if (response) {
      form.value = { ...response }
      isNew.value = false
      currentId.value = response.id
    }
  } catch (error) {
    ElMessage.error('加载最新期初余额失败')
  }
}

onMounted(() => {
  loadOpeningBalances()
})
</script>

<style scoped>
.opening-balance-container {
  padding: 20px;
}

.history-card {
  margin-top: 20px;
}

.el-divider {
  margin: 20px 0;
}

.el-form-item {
  margin-bottom: 15px;
}

.el-alert {
  margin-bottom: 20px;
}
</style>