<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">期初余额设置</span>
          <el-button v-if="isEdit" text type="info" @click="resetForm">取消编辑</el-button>
        </div>
      </template>

      <el-form :model="form" :rules="rules" ref="formRef">
        <div class="ob-date">
          <span class="ob-date-label">期初日期</span>
          <el-date-picker v-model="form.date" type="date" placeholder="选择日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width:200px" />
        </div>

        <div class="ob-groups">
          <div v-for="(g, gi) in groups" :key="gi" class="ob-group" :style="{ borderLeftColor: g.color }">
            <div class="ob-group-header">
              <span class="ob-group-tag" :style="{ background: g.bg, color: g.color }">{{ g.label }}</span>
            </div>
            <div class="ob-group-body">
              <div v-for="f in g.fields" :key="f.key" class="ob-field">
                <span class="ob-field-label">{{ f.label }}</span>
                <el-input-number
                  v-model="form[f.key]"
                  :precision="2"
                  :min="0"
                  controls-position="right"
                  style="width:100%"
                  size="small"
                />
              </div>
            </div>
          </div>
        </div>

        <div class="ob-bar" :class="isBalanced ? 'ob-bar-ok' : 'ob-bar-err'">
          <div class="ob-bar-left">
            <span class="ob-bar-icon">{{ isBalanced ? '✓' : '✗' }}</span>
            <span>{{ isBalanced ? '资产负债平衡' : '资产负债不平衡' }}</span>
          </div>
          <div class="ob-bar-right">
            <span>资产 {{ formatMoney(totalAssets) }}</span>
            <span class="ob-bar-vs">=</span>
            <span>负债 {{ formatMoney(totalLiabilities) }}</span>
            <span class="ob-bar-vs">+</span>
            <span>权益 {{ formatMoney(totalEquity) }}</span>
          </div>
        </div>

        <div style="display:flex;gap:12px;margin-top:20px;">
          <el-button type="primary" @click="handleSave" :loading="saving" size="large">{{ isEdit ? '更新期初' : '保存期初' }}</el-button>
          <el-button @click="resetForm">重置</el-button>
        </div>
      </el-form>

      <div class="ob-history">
        <div class="ob-history-title">历史记录</div>
        <el-table :data="historyList" stripe style="width:100%" v-loading="historyLoading">
          <template #empty><el-empty description="暂无历史记录" /></template>
          <el-table-column prop="date" label="期初日期" min-width="120" />
          <el-table-column label="资产" min-width="120" align="right">
            <template #default="{ row }"><span class="money">¥{{ formatMoney(calculateTotalAssets(row)) }}</span></template>
          </el-table-column>
          <el-table-column label="负债" min-width="120" align="right">
            <template #default="{ row }"><span class="money">¥{{ formatMoney(calculateTotalLiabilities(row)) }}</span></template>
          </el-table-column>
          <el-table-column label="权益" min-width="120" align="right">
            <template #default="{ row }"><span class="money">¥{{ formatMoney(calculateTotalEquity(row)) }}</span></template>
          </el-table-column>
          <el-table-column label="操作" width="150" fixed="right">
            <template #default="{ row }">
              <el-button size="small" link type="primary" @click="loadForEdit(row)">编辑</el-button>
              <el-popconfirm title="确定删除？" @confirm="handleDelete(row.id)">
                <template #reference><el-button size="small" link type="danger">删除</el-button></template>
              </el-popconfirm>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import financeApi from '../api/finance'
import { formatMoney } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../utils/errorHandler'

const formRef = ref(null)
const saving = ref(false)
const isEdit = ref(false)
const historyList = ref([])
const historyLoading = ref(false)

const defaultForm = () => ({
  date: new Date().toISOString().split('T')[0],
  cash_balance: 0, bank_balance: 0, accounts_receivable: 0, inventory_value: 0,
  fixed_assets_original: 0, accumulated_depreciation: 0, intangible_assets_original: 0, accumulated_amortization: 0,
  accounts_payable: 0, tax_payable: 0,
  long_term_borrowings: 0,
  paid_in_capital: 0, retained_earnings: 0
})

const form = ref(defaultForm())
const rules = { date: [{ required: true, message: '请选择期初日期', trigger: 'change' }] }

const groups = [
  { label: '流动资产', color: '#4f6ef7', bg: '#eef1ff', fields: [
    { key: 'cash_balance', label: '现金余额' },
    { key: 'bank_balance', label: '银行存款' },
    { key: 'accounts_receivable', label: '应收账款' },
    { key: 'inventory_value', label: '库存价值' },
  ]},
  { label: '非流动资产', color: '#e6a23c', bg: '#fdf6ec', fields: [
    { key: 'fixed_assets_original', label: '固定资产原值' },
    { key: 'accumulated_depreciation', label: '累计折旧' },
    { key: 'intangible_assets_original', label: '无形资产原值' },
    { key: 'accumulated_amortization', label: '累计摊销' },
  ]},
  { label: '流动负债', color: '#f56c6c', bg: '#fef0f0', fields: [
    { key: 'accounts_payable', label: '应付账款' },
    { key: 'tax_payable', label: '应交税费' },
  ]},
  { label: '非流动负债', color: '#67c23a', bg: '#f0f9eb', fields: [
    { key: 'long_term_borrowings', label: '长期借款' },
  ]},
  { label: '权益', color: '#4f6ef7', bg: '#f4f6ff', fields: [
    { key: 'paid_in_capital', label: '实收资本' },
    { key: 'retained_earnings', label: '未分配利润' },
  ]},
]

const totalAssets = computed(() =>
  Number(form.value.cash_balance || 0) + Number(form.value.bank_balance || 0) +
  Number(form.value.accounts_receivable || 0) + Number(form.value.inventory_value || 0) +
  Number(form.value.fixed_assets_original || 0) - Number(form.value.accumulated_depreciation || 0) +
  Number(form.value.intangible_assets_original || 0) - Number(form.value.accumulated_amortization || 0)
)
const totalLiabilities = computed(() =>
  Number(form.value.accounts_payable || 0) + Number(form.value.tax_payable || 0) +
  Number(form.value.long_term_borrowings || 0)
)
const totalEquity = computed(() =>
  Number(form.value.paid_in_capital || 0) + Number(form.value.retained_earnings || 0)
)
const isBalanced = computed(() => Math.abs(totalAssets.value - (totalLiabilities.value + totalEquity.value)) < 0.01)

function calculateTotalAssets(r) {
  return Number(r.cash_balance || 0) + Number(r.bank_balance || 0) + Number(r.accounts_receivable || 0) +
    Number(r.inventory_value || 0) + Number(r.fixed_assets_original || 0) - Number(r.accumulated_depreciation || 0) +
    Number(r.intangible_assets_original || 0) - Number(r.accumulated_amortization || 0)
}
function calculateTotalLiabilities(r) {
  return Number(r.accounts_payable || 0) + Number(r.tax_payable || 0) + Number(r.long_term_borrowings || 0)
}
function calculateTotalEquity(r) {
  return Number(r.paid_in_capital || 0) + Number(r.retained_earnings || 0)
}

async function loadData() {
  historyLoading.value = true
  try { const res = await financeApi.getOpeningBalances(); historyList.value = res.items || res }
  catch (e) { console.error('加载失败:', e) }
  finally { historyLoading.value = false }
}

async function handleSave() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  if (!isBalanced.value) { ElMessage.error('资产负债不平衡，无法保存'); return }
  saving.value = true
  try {
    if (isEdit.value && form.value.id) {
      await financeApi.updateOpeningBalance(form.value.id, form.value)
      ElMessage.success('更新成功')
    } else {
      await financeApi.createOpeningBalance(form.value)
      ElMessage.success('保存成功')
    }
    resetForm(); loadData()
  } catch (e) { handleError(e, { defaultMsg: '保存失败，请检查输入数据是否正确并确保借贷平衡' }) }
  finally { saving.value = false }
}

function resetForm() {
  form.value = defaultForm(); isEdit.value = false
  if (formRef.value) formRef.value.clearValidate()
}

async function loadForEdit(row) {
  try {
    const detail = await financeApi.getOpeningBalanceById(row.id)
    form.value = { ...detail }; isEdit.value = true
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (e) { handleError(e, { defaultMsg: '加载期初余额失败，请检查网络连接' }) }
}

async function handleDelete(id) {
  try { await financeApi.deleteOpeningBalance(id); ElMessage.success('删除成功'); loadData() }
  catch (e) { handleError(e, { defaultMsg: '删除失败，请检查该期初余额是否可删除' }) }
}

useAccountAwareData(loadData)
</script>

<style scoped>
.ob-date {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #f0f0f0;
}
.ob-date-label {
  font-size: 14px;
  font-weight: 600;
  color: #1d2129;
}

.ob-groups {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}
.ob-group {
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-left: 4px solid;
  border-radius: 12px;
  overflow: hidden;
}
.ob-group-header {
  padding: 12px 16px 8px;
}
.ob-group-tag {
  display: inline-block;
  padding: 2px 12px;
  border-radius: 9999px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.5px;
}
.ob-group-body {
  padding: 4px 16px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.ob-field {
  display: flex;
  align-items: center;
  gap: 12px;
}
.ob-field-label {
  font-size: 13px;
  color: #4e5969;
  min-width: 90px;
  flex-shrink: 0;
}

.ob-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 18px;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 500;
}
.ob-bar-ok {
  background: #f0f9eb;
  color: #67c23a;
}
.ob-bar-err {
  background: #fef0f0;
  color: #f56c6c;
}
.ob-bar-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ob-bar-icon {
  font-weight: 700;
  font-size: 18px;
}
.ob-bar-right {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-family: 'Consolas', 'Monaco', monospace;
}
.ob-bar-right span { font-weight: 600; }
.ob-bar-vs {
  color: #c9cdd4;
  font-weight: 400 !important;
}

.ob-history {
  margin-top: 28px;
  padding-top: 24px;
  border-top: 1px solid #f0f0f0;
}
.ob-history-title {
  font-size: 15px;
  font-weight: 600;
  color: #1d2129;
  margin-bottom: 12px;
}
</style>
