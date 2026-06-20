<template>
  <div class="opening-balance-tab">
    <el-card shadow="never">
      <template #header>
        <span style="font-weight:600;">期初余额设置</span>
      </template>
    
    <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
      <el-row :gutter="20">
        <el-col :span="12">
          <el-form-item label="期初日期" prop="date">
            <el-date-picker v-model="form.date" type="date" placeholder="选择日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" />
          </el-form-item>
        </el-col>
      </el-row>
      
      <el-divider>流动资产类</el-divider>
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
      
      <el-divider>非流动资产类</el-divider>
      <el-row :gutter="20">
        <el-col :span="8">
          <el-form-item label="固定资产原值" prop="fixed_assets_original">
            <el-input-number v-model="form.fixed_assets_original" :precision="2" :min="0" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="累计折旧" prop="accumulated_depreciation">
            <el-input-number v-model="form.accumulated_depreciation" :precision="2" :min="0" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="无形资产原值" prop="intangible_assets_original">
            <el-input-number v-model="form.intangible_assets_original" :precision="2" :min="0" style="width: 100%" />
          </el-form-item>
        </el-col>
      </el-row>
      <el-row :gutter="20">
        <el-col :span="8">
          <el-form-item label="累计摊销" prop="accumulated_amortization">
            <el-input-number v-model="form.accumulated_amortization" :precision="2" :min="0" style="width: 100%" />
          </el-form-item>
        </el-col>
      </el-row>
      
      <el-divider>流动负债类</el-divider>
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
      
      <el-divider>非流动负债类</el-divider>
      <el-row :gutter="20">
        <el-col :span="8">
          <el-form-item label="长期借款" prop="long_term_borrowings">
            <el-input-number v-model="form.long_term_borrowings" :precision="2" :min="0" style="width: 100%" />
          </el-form-item>
        </el-col>
      </el-row>
      
      <el-divider>权益类</el-divider>
      <el-row :gutter="20">
        <el-col :span="8">
          <el-form-item label="实收资本" prop="paid_in_capital">
            <el-input-number v-model="form.paid_in_capital" :precision="2" :min="0" style="width: 100%" />
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="未分配利润" prop="retained_earnings">
            <el-input-number v-model="form.retained_earnings" :precision="2" :min="0" style="width: 100%" />
          </el-form-item>
        </el-col>
      </el-row>

      <!-- 资产负债平衡校验 -->
      <el-alert 
        v-if="!isBalanced" 
        title="资产负债不平衡，请检查输入数据" 
        type="error" 
        :closable="false"
        show-icon
        style="margin-bottom: 16px;"
      >
        <template #default>
          <div>资产总计: ¥{{ formatMoney(totalAssets) }} ≠ 负债 + 权益: ¥{{ formatMoney(totalLiabilitiesAndEquity) }}</div>
        </template>
      </el-alert>
      <el-alert 
        v-else
        title="资产负债平衡 ✓" 
        type="success" 
        :closable="false"
        show-icon
        style="margin-bottom: 16px;"
      />
      
      <el-form-item>
        <el-button type="primary" @click="handleSave" :loading="saving">{{ isEdit ? '更新' : '保存' }}</el-button>
        <el-button @click="resetForm">重置</el-button>
      </el-form-item>
    </el-form>

    <!-- 历史记录 -->
    <el-divider>历史记录</el-divider>
    <el-table :data="historyList" stripe style="width:100%" v-loading="historyLoading">
      <template #empty>
        <el-empty description="暂无历史记录" />
      </template>
      <el-table-column prop="date" label="期初日期" width="120" />
      <el-table-column label="资产总计" width="140" align="right">
        <template #default="{ row }">
          <span class="money">¥{{ formatMoney(calculateTotalAssets(row)) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="负债总计" width="140" align="right">
        <template #default="{ row }">
          <span class="money">¥{{ formatMoney(calculateTotalLiabilities(row)) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="权益总计" width="140" align="right">
        <template #default="{ row }">
          <span class="money">¥{{ formatMoney(calculateTotalEquity(row)) }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button size="small" link type="primary" @click="loadForEdit(row)">编辑</el-button>
          <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)">
            <template #reference>
              <el-button size="small" link type="danger">删除</el-button>
            </template>
          </el-popconfirm>
        </template>
      </el-table-column>
    </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import financeApi from '../api/finance'
import { formatMoney } from '../api/common'
import { useAccountAwareData } from '../composables/useAccountAwareData'

const formRef = ref(null)
const saving = ref(false)
const isEdit = ref(false)
const historyList = ref([])
const historyLoading = ref(false)

const defaultForm = () => ({
  date: new Date().toISOString().split('T')[0],
  cash_balance: 0,
  bank_balance: 0,
  accounts_receivable: 0,
  inventory_value: 0,
  fixed_assets_original: 0,
  accumulated_depreciation: 0,
  intangible_assets_original: 0,
  accumulated_amortization: 0,
  accounts_payable: 0,
  tax_payable: 0,
  long_term_borrowings: 0,
  paid_in_capital: 0,
  retained_earnings: 0
})

const form = ref(defaultForm())

const rules = {
  date: [{ required: true, message: '请选择期初日期', trigger: 'change' }]
}

// 计算总资产
const totalAssets = computed(() => {
  return (
    Number(form.value.cash_balance || 0) +
    Number(form.value.bank_balance || 0) +
    Number(form.value.accounts_receivable || 0) +
    Number(form.value.inventory_value || 0) +
    Number(form.value.fixed_assets_original || 0) -
    Number(form.value.accumulated_depreciation || 0) +
    Number(form.value.intangible_assets_original || 0) -
    Number(form.value.accumulated_amortization || 0)
  )
})

// 计算总负债
const totalLiabilities = computed(() => {
  return (
    Number(form.value.accounts_payable || 0) +
    Number(form.value.tax_payable || 0) +
    Number(form.value.long_term_borrowings || 0)
  )
})

// 计算总权益
const totalEquity = computed(() => {
  return (
    Number(form.value.paid_in_capital || 0) +
    Number(form.value.retained_earnings || 0)
  )
})

// 负债+权益
const totalLiabilitiesAndEquity = computed(() => {
  return totalLiabilities.value + totalEquity.value
})

// 是否平衡
const isBalanced = computed(() => {
  return Math.abs(totalAssets.value - totalLiabilitiesAndEquity.value) < 0.01
})

function calculateTotalAssets(row) {
  return (
    Number(row.cash_balance || 0) +
    Number(row.bank_balance || 0) +
    Number(row.accounts_receivable || 0) +
    Number(row.inventory_value || 0) +
    Number(row.fixed_assets_original || 0) -
    Number(row.accumulated_depreciation || 0) +
    Number(row.intangible_assets_original || 0) -
    Number(row.accumulated_amortization || 0)
  )
}

function calculateTotalLiabilities(row) {
  return (
    Number(row.accounts_payable || 0) +
    Number(row.tax_payable || 0) +
    Number(row.long_term_borrowings || 0)
  )
}

function calculateTotalEquity(row) {
  return (
    Number(row.paid_in_capital || 0) +
    Number(row.retained_earnings || 0)
  )
}

async function loadData() {
  historyLoading.value = true
  try {
    const res = await financeApi.getOpeningBalances()
    historyList.value = res.items || res
  } catch (e) {
    console.error('加载历史记录失败:', e)
  } finally {
    historyLoading.value = false
  }
}

async function handleSave() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  if (!isBalanced.value) {
    ElMessage.error('资产负债不平衡，无法保存')
    return
  }

  saving.value = true
  try {
    if (isEdit.value && form.value.id) {
      await financeApi.updateOpeningBalance(form.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await financeApi.createOpeningBalance(form.value)
      ElMessage.success('保存成功')
    }
    resetForm()
    loadData()
  } catch (e) {
    ElMessage.error('保存失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

function resetForm() {
  form.value = defaultForm()
  isEdit.value = false
  if (formRef.value) {
    formRef.value.clearValidate()
  }
}

async function loadForEdit(row) {
  try {
    const detail = await financeApi.getOpeningBalanceById(row.id)
    form.value = { ...detail }
    isEdit.value = true
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (e) {
    ElMessage.error('加载详情失败')
  }
}

async function handleDelete(id) {
  try {
    await financeApi.deleteOpeningBalance(id)
    ElMessage.success('删除成功')
    loadData()
  } catch (e) {
    ElMessage.error('删除失败: ' + (e.response?.data?.detail || e.message))
  }
}

useAccountAwareData(loadData)
</script>

<style scoped>
.opening-balance-tab {
  padding: 0;
}
</style>
