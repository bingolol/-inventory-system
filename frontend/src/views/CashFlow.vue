<template>
  <div class="cf-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">现金流量表</span>
          <el-button type="primary" @click="showNewTransaction">
            <el-icon><Plus /></el-icon> 新增现金流水
          </el-button>
        </div>
      </template>
      <div class="filter-bar">
        <el-date-picker v-model="queryForm.startDate" type="date" placeholder="开始日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" />
        <el-date-picker v-model="queryForm.endDate" type="date" placeholder="结束日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" />
        <el-button type="primary" @click="getCashFlowStatement">查询</el-button>
      </div>
    </el-card>

    <el-card v-if="cashFlowStatement" class="cf-report">
      <div class="cf-period">{{ cashFlowStatement.period }}</div>
      <div class="cf-grid">
        <div class="cf-section" v-for="(s, i) in flowSections" :key="i">
          <div class="cf-section-bar" :style="{ background: s.color }"></div>
          <div class="cf-section-body">
            <div class="cf-section-title">{{ s.title }}</div>
            <div class="cf-section-stats">
              <div class="cf-stat">
                <span class="cf-stat-label">现金流入</span>
                <span class="cf-stat-value c-success">{{ formatMoney(s.data.inflows) }}</span>
              </div>
              <div class="cf-stat">
                <span class="cf-stat-label">现金流出</span>
                <span class="cf-stat-value c-danger">{{ formatMoney(s.data.outflows) }}</span>
              </div>
              <div class="cf-stat">
                <span class="cf-stat-label">净现金流</span>
                <span class="cf-stat-value" :style="{ color: s.data.net >= 0 ? '#409eff' : '#f56c6c' }">
                  {{ formatMoney(s.data.net) }}
                  <span class="cf-stat-tag" :class="s.data.net >= 0 ? 'pos' : 'neg'">
                    {{ s.data.net >= 0 ? '净流入' : '净流出' }}
                  </span>
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div class="cf-total">
        <div class="cf-total-row">
          <span>净现金流量</span>
          <span style="font-weight:700;font-size:18px;" :style="{ color: cashFlowStatement.net_cash_flow >= 0 ? '#409eff' : '#f56c6c' }">
            {{ formatMoney(cashFlowStatement.net_cash_flow) }}
          </span>
        </div>
        <div class="cf-total-row">
          <span>期初余额</span>
          <span>{{ formatMoney(cashFlowStatement.beginning_cash_balance) }}</span>
        </div>
        <div class="cf-total-row">
          <span>期末余额</span>
          <span style="font-weight:700;font-size:16px;">{{ formatMoney(cashFlowStatement.ending_cash_balance) }}</span>
        </div>
        <div class="cf-formula">
          经营{{ formatMoney(cashFlowStatement.operating_activities.net) }}
          + 投资{{ formatMoney(cashFlowStatement.investing_activities.net) }}
          + 筹资{{ formatMoney(cashFlowStatement.financing_activities.net) }}
          = 净现金流 {{ formatMoney(cashFlowStatement.net_cash_flow) }}
        </div>
      </div>
    </el-card>

    <el-card class="cf-table-card">
      <template #header>
        <span style="font-weight:600;font-size:15px;">现金流水记录</span>
      </template>
      <el-table :data="cashFlowTransactions" style="width:100%" v-loading="loading">
        <template #empty><el-empty description="暂无现金流水记录" /></template>
        <el-table-column label="日期" min-width="120">
          <template #default="{ row }">{{ formatDate(row.transaction_date) }}</template>
        </el-table-column>
        <el-table-column prop="type" label="类型" min-width="80" align="center">
          <template #default="scope">
            <span class="status-badge" :class="scope.row.type === 'inflow' ? 'success' : 'danger'">
              {{ scope.row.type === 'inflow' ? '流入' : '流出' }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="flow_category" label="分类" min-width="100" align="center">
          <template #default="scope">
            <span class="status-badge" :class="getCategoryClass(scope.row.flow_category)">
              {{ getCategoryLabel(scope.row.flow_category) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="金额" min-width="120" align="right">
          <template #default="scope">{{ formatMoney(scope.row.amount) }}</template>
        </el-table-column>
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="related_entity_type" label="关联类型" min-width="100" align="center" />
        <el-table-column label="操作" width="150" align="center">
          <template #default="scope">
            <el-button size="small" link type="primary" @click="showEditTransaction(scope.row)">编辑</el-button>
            <el-popconfirm title="确定删除此现金流水？" @confirm="handleDeleteTransaction(scope.row.id)">
              <template #reference><el-button size="small" link type="danger">删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="showAddDialog" :title="editingTransactionId ? '编辑现金流水' : '新增现金流水'" width="500px">
      <el-form :model="newTransaction" label-width="100px">
        <el-form-item label="类型" required>
          <el-radio-group v-model="newTransaction.type">
            <el-radio value="inflow">流入</el-radio>
            <el-radio value="outflow">流出</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="金额" required>
          <el-input-number v-model="newTransaction.amount" :min="0.01" :precision="2" style="width:100%;" />
        </el-form-item>
        <el-form-item label="分类" required>
          <el-select v-model="newTransaction.flow_category" placeholder="请选择分类">
            <el-option label="经营活动" value="operating" />
            <el-option label="投资活动" value="investing" />
            <el-option label="筹资活动" value="financing" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期" required>
          <el-date-picker v-model="newTransaction.transaction_date" type="date" placeholder="选择日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width:100%;" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="newTransaction.description" type="textarea" placeholder="请输入描述" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="saveTransaction">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import financeApi from '../api/finance'
import { formatMoney } from '../utils/format'
import { handleError } from '../api/index'
import { useAccountAwareData } from '../composables/useAccountAwareData'

const queryForm = ref({
  startDate: new Date(new Date().getFullYear(), 0, 1).toISOString().split('T')[0],
  endDate: new Date().toISOString().split('T')[0]
})

const cashFlowStatement = ref(null)
const cashFlowTransactions = ref([])
const loading = ref(false)
const showAddDialog = ref(false)
const editingTransactionId = ref(null)
const newTransaction = ref({
  type: 'outflow', amount: 0, flow_category: 'operating',
  transaction_date: new Date().toISOString().split('T')[0], description: ''
})

const flowSections = computed(() => {
  const s = cashFlowStatement.value
  if (!s) return []
  return [
    { title: '一、经营活动产生的现金流量', color: '#409eff', data: s.operating_activities },
    { title: '二、投资活动产生的现金流量', color: '#67c23a', data: s.investing_activities },
    { title: '三、筹资活动产生的现金流量', color: '#e6a23c', data: s.financing_activities },
  ]
})

const getCashFlowStatement = async () => {
  loading.value = true
  try {
    cashFlowStatement.value = await financeApi.getCashFlowStatement(queryForm.value.startDate, queryForm.value.endDate)
  } catch (error) {
    handleError(error, { defaultMsg: '获取现金流量表失败，请检查本期是否有现金流水数据' })
  } finally {
    loading.value = false
  }
}

const loadTransactions = async () => {
  try {
    const res = await financeApi.getCashFlowTransactions({
      start_date: queryForm.value.startDate, end_date: queryForm.value.endDate, limit: 100
    })
    cashFlowTransactions.value = res.items || []
  } catch (error) {
    handleError(error, { defaultMsg: '获取现金流水失败，请检查网络连接', feedback: 'silent' })
  }
}

const showNewTransaction = () => {
  editingTransactionId.value = null
  newTransaction.value = { type: 'outflow', amount: 0, flow_category: 'operating', transaction_date: new Date().toISOString().split('T')[0], description: '' }
  showAddDialog.value = true
}

const showEditTransaction = (row) => {
  editingTransactionId.value = row.id
  newTransaction.value = { type: row.type, amount: row.amount, flow_category: row.flow_category, transaction_date: row.transaction_date?.split('T')[0] || '', description: row.description || '' }
  showAddDialog.value = true
}

const handleDeleteTransaction = async (id) => {
  try {
    await financeApi.deleteCashFlowTransaction(id)
    ElMessage.success('已删除')
    getCashFlowStatement()
    loadTransactions()
  } catch (e) { handleError(e, { defaultMsg: '删除失败，请检查该流水是否可删除' }) }
}

const saveTransaction = async () => {
  try {
    if (editingTransactionId.value) {
      await financeApi.updateCashFlowTransaction(editingTransactionId.value, newTransaction.value)
      ElMessage.success('更新成功')
    } else {
      await financeApi.createCashFlowTransaction(newTransaction.value)
      ElMessage.success('创建成功')
    }
    showAddDialog.value = false
    editingTransactionId.value = null
    newTransaction.value = { type: 'outflow', amount: 0, flow_category: 'operating', transaction_date: new Date().toISOString().split('T')[0], description: '' }
    getCashFlowStatement()
    loadTransactions()
  } catch (error) {
    handleError(error, { defaultMsg: editingTransactionId.value ? '更新失败，请检查输入数据是否正确' : '创建失败，请检查输入数据是否正确' })
  }
}

const getCategoryClass = (cat) => {
  const map = { operating: 'primary', investing: 'warning', financing: 'info' }
  return map[cat] || ''
}

const getCategoryLabel = (cat) => {
  const map = { operating: '经营', investing: '投资', financing: '筹资' }
  return map[cat] || cat
}

useAccountAwareData(getCashFlowStatement, loadTransactions)
</script>

<style scoped>
.cf-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.cf-report {
  animation: cfFadeIn 0.4s ease;
}
@keyframes cfFadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}
.cf-period {
  font-size: 13px;
  color: #86909c;
  margin-bottom: 16px;
}
.cf-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 20px;
}
.cf-section {
  background: #fafafa;
  border-radius: 12px;
  border: 1px solid #f0f0f0;
  display: flex;
  overflow: hidden;
}
.cf-section-bar {
  width: 4px;
  flex-shrink: 0;
}
.cf-section-body {
  flex: 1;
  padding: 16px;
}
.cf-section-title {
  font-size: 14px;
  font-weight: 600;
  color: #1d2129;
  margin-bottom: 14px;
}
.cf-section-stats {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.cf-stat {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}
.cf-stat-label {
  color: #86909c;
}
.cf-stat-value {
  font-weight: 600;
  font-family: 'Consolas', 'Monaco', monospace;
}
.cf-stat-tag {
  display: inline-block;
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 9999px;
  margin-left: 6px;
  font-weight: 500;
  font-family: -apple-system, sans-serif;
}
.cf-stat-tag.pos { background: #ecf5ff; color: #409eff; }
.cf-stat-tag.neg { background: #fef0f0; color: #f56c6c; }
.cf-total {
  background: linear-gradient(135deg, #f0f7ff, #ecf5ff);
  border-radius: 12px;
  padding: 16px 20px;
  display: flex;
  gap: 40px;
}
.cf-total-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 13px;
  color: #86909c;
}
.cf-formula {
  font-size: 12px;
  color: #c9cdd4;
  font-family: 'Consolas', 'Monaco', monospace;
  border-top: 1px solid rgba(255,255,255,0.3);
  padding-top: 8px;
  margin-top: 4px;
  grid-column: 1 / -1;
}
.cf-table-card {
  margin-top: 0;
}

@media (max-width: 1200px) {
  .cf-grid { grid-template-columns: 1fr; }
  .cf-total { flex-wrap: wrap; gap: 16px; }
}
</style>
