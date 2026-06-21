<template>
  <div class="cash-flow-container">
    <el-card shadow="never">
      <template #header>
        <span style="font-weight:600;">现金流量表</span>
      </template>

    <!-- 期间选择 -->
    <el-form :inline="true" :model="queryForm" class="query-form">
      <el-form-item label="开始日期">
        <el-date-picker v-model="queryForm.startDate" type="date" placeholder="开始日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" />
      </el-form-item>
      <el-form-item label="结束日期">
        <el-date-picker v-model="queryForm.endDate" type="date" placeholder="结束日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" @click="getCashFlowStatement">查询</el-button>
      </el-form-item>
      <el-form-item>
        <el-button type="success" @click="showNewTransaction">新增现金流水</el-button>
      </el-form-item>
    </el-form>
    </el-card>

    <!-- 现金流量表 -->
    <el-card v-if="cashFlowStatement" class="report-card">
      <template #header>
        <div class="card-header">
          <span>现金流量表 ({{ cashFlowStatement.period }})</span>
        </div>
      </template>

      <!-- 经营活动 -->
      <div class="flow-section">
        <div class="flow-title">一、经营活动产生的现金流量</div>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-statistic title="现金流入" :value="cashFlowStatement.operating_activities.inflows" :precision="2" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="现金流出" :value="cashFlowStatement.operating_activities.outflows" :precision="2" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="经营活动净现金流" :value="cashFlowStatement.operating_activities.net" :precision="2">
              <template #suffix>
                <el-tag size="small" :type="cashFlowStatement.operating_activities.net >= 0 ? 'success' : 'danger'">
                  {{ cashFlowStatement.operating_activities.net >= 0 ? '净流入' : '净流出' }}
                </el-tag>
              </template>
            </el-statistic>
          </el-col>
        </el-row>
      </div>

      <el-divider />

      <!-- 投资活动 -->
      <div class="flow-section">
        <div class="flow-title">二、投资活动产生的现金流量</div>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-statistic title="现金流入" :value="cashFlowStatement.investing_activities.inflows" :precision="2" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="现金流出" :value="cashFlowStatement.investing_activities.outflows" :precision="2" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="投资活动净现金流" :value="cashFlowStatement.investing_activities.net" :precision="2">
              <template #suffix>
                <el-tag size="small" :type="cashFlowStatement.investing_activities.net >= 0 ? 'success' : 'danger'">
                  {{ cashFlowStatement.investing_activities.net >= 0 ? '净流入' : '净流出' }}
                </el-tag>
              </template>
            </el-statistic>
          </el-col>
        </el-row>
      </div>

      <el-divider />

      <!-- 筹资活动 -->
      <div class="flow-section">
        <div class="flow-title">三、筹资活动产生的现金流量</div>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-statistic title="现金流入" :value="cashFlowStatement.financing_activities.inflows" :precision="2" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="现金流出" :value="cashFlowStatement.financing_activities.outflows" :precision="2" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="筹资活动净现金流" :value="cashFlowStatement.financing_activities.net" :precision="2">
              <template #suffix>
                <el-tag size="small" :type="cashFlowStatement.financing_activities.net >= 0 ? 'success' : 'danger'">
                  {{ cashFlowStatement.financing_activities.net >= 0 ? '净流入' : '净流出' }}
                </el-tag>
              </template>
            </el-statistic>
          </el-col>
        </el-row>
      </div>

      <el-divider />

      <!-- 汇总 -->
      <div class="flow-section">
        <div class="flow-title">四、现金及现金等价物净增加额</div>
        <el-row :gutter="20">
          <el-col :span="8">
            <el-statistic title="净现金流量" :value="cashFlowStatement.net_cash_flow" :precision="2">
              <template #suffix>
                <el-tag size="small" :type="cashFlowStatement.net_cash_flow >= 0 ? 'success' : 'danger'">
                  {{ cashFlowStatement.net_cash_flow >= 0 ? '增加' : '减少' }}
                </el-tag>
              </template>
            </el-statistic>
          </el-col>
          <el-col :span="8">
            <el-statistic title="期初现金余额" :value="cashFlowStatement.beginning_cash_balance" :precision="2" />
          </el-col>
          <el-col :span="8">
            <el-statistic title="期末现金余额" :value="cashFlowStatement.ending_cash_balance" :precision="2" />
          </el-col>
        </el-row>
      </div>
    </el-card>

    <!-- 现金流水列表 -->
    <el-card class="transaction-card" style="margin-top: 20px;">
      <template #header>
        <span>现金流水记录</span>
      </template>
      <el-table :data="cashFlowTransactions" style="width: 100%" v-loading="loading">
        <template #empty>
          <el-empty description="暂无现金流水记录" />
        </template>
        <el-table-column prop="transaction_date" label="日期" width="120">
          <template #default="{ row }">
            {{ row.transaction_date?.split('T')[0] }}
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="80">
          <template #default="scope">
            <el-tag :type="scope.row.type === 'inflow' ? 'success' : 'danger'">
              {{ scope.row.type === 'inflow' ? '流入' : '流出' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="flow_category" label="分类" width="100">
          <template #default="scope">
            <el-tag :type="getCategoryType(scope.row.flow_category)">
              {{ getCategoryLabel(scope.row.flow_category) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="金额" width="120" align="right">
          <template #default="scope">{{ formatMoney(scope.row.amount) }}</template>
        </el-table-column>
        <el-table-column prop="description" label="描述" />
        <el-table-column prop="related_entity_type" label="关联类型" width="100" />
        <el-table-column label="操作" width="150" align="center">
          <template #default="scope">
            <el-button size="small" link type="primary" @click="showEditTransaction(scope.row)">编辑</el-button>
            <el-popconfirm title="确定删除此现金流水？" @confirm="handleDeleteTransaction(scope.row.id)">
              <template #reference>
                <el-button size="small" link type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 新增现金流水弹窗 -->
    <el-dialog v-model="showAddDialog" :title="editingTransactionId ? '编辑现金流水' : '新增现金流水'" width="500px">
      <el-form :model="newTransaction" label-width="100px">
        <el-form-item label="类型" required>
          <el-radio-group v-model="newTransaction.type">
            <el-radio value="inflow">流入</el-radio>
            <el-radio value="outflow">流出</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="金额" required>
          <el-input-number v-model="newTransaction.amount" :min="0.01" :precision="2" style="width: 100%;" />
        </el-form-item>
        <el-form-item label="分类" required>
          <el-select v-model="newTransaction.flow_category" placeholder="请选择分类">
            <el-option label="经营活动" value="operating" />
            <el-option label="投资活动" value="investing" />
            <el-option label="筹资活动" value="financing" />
          </el-select>
        </el-form-item>
        <el-form-item label="日期" required>
          <el-date-picker v-model="newTransaction.transaction_date" type="date" placeholder="选择日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" style="width: 100%;" />
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
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
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
  type: 'outflow',
  amount: 0,
  flow_category: 'operating',
  transaction_date: new Date().toISOString().split('T')[0],
  description: ''
})

const getCashFlowStatement = async () => {
  loading.value = true
  try {
    cashFlowStatement.value = await financeApi.getCashFlowStatement(queryForm.value.startDate, queryForm.value.endDate)
  } catch (error) {
    handleError(error, { defaultMsg: '获取现金流量表失败' })
  } finally {
    loading.value = false
  }
}

const loadTransactions = async () => {
  try {
    const res = await financeApi.getCashFlowTransactions({
      start_date: queryForm.value.startDate,
      end_date: queryForm.value.endDate,
      limit: 100
    })
    cashFlowTransactions.value = res.items || []
  } catch (error) {
    handleError(error, { defaultMsg: '获取现金流水失败', feedback: 'silent' })
  }
}

const showNewTransaction = () => {
  editingTransactionId.value = null
  newTransaction.value = {
    type: 'outflow',
    amount: 0,
    flow_category: 'operating',
    transaction_date: new Date().toISOString().split('T')[0],
    description: ''
  }
  showAddDialog.value = true
}

const showEditTransaction = (row) => {
  editingTransactionId.value = row.id
  newTransaction.value = {
    type: row.type,
    amount: row.amount,
    flow_category: row.flow_category,
    transaction_date: row.transaction_date?.split('T')[0] || '',
    description: row.description || ''
  }
  showAddDialog.value = true
}

const handleDeleteTransaction = async (id) => {
  try {
    await financeApi.deleteCashFlowTransaction(id)
    ElMessage.success('已删除')
    getCashFlowStatement()
    loadTransactions()
  } catch (e) { handleError(e, { defaultMsg: '删除失败' }) }
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
    newTransaction.value = {
      type: 'outflow',
      amount: 0,
      flow_category: 'operating',
      transaction_date: new Date().toISOString().split('T')[0],
      description: ''
    }
    getCashFlowStatement()
    loadTransactions()
  } catch (error) {
    handleError(error, { defaultMsg: editingTransactionId.value ? '更新失败' : '创建失败' })
  }
}

const getCategoryType = (cat) => {
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
.cash-flow-container {
  padding: 20px;
}

.query-form {
  margin-bottom: 20px;
  padding: 10px;
  background-color: #f5f7fa;
  border-radius: 4px;
}

.report-card {
  margin-top: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.flow-section {
  padding: 15px 0;
}

.flow-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 15px;
}

.transaction-card {
  margin-top: 20px;
}
</style>