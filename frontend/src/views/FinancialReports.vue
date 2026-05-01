<template>
  <div class="financial-reports-container">
    <h2>财务报表</h2>
    
    <!-- 报表类型选择 -->
    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <el-tab-pane label="资产负债表" name="balance-sheet">
        <BalanceSheet :date="reportDate" />
      </el-tab-pane>
      <el-tab-pane label="利润表" name="income-statement">
        <IncomeStatement :start-date="startDate" :end-date="endDate" />
      </el-tab-pane>
      <el-tab-pane label="财务汇总" name="summary">
        <FinancialSummary :date="reportDate" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import BalanceSheet from '../components/BalanceSheet.vue'
import IncomeStatement from '../components/IncomeStatement.vue'
import FinancialSummary from '../components/FinancialSummary.vue'

const activeTab = ref('balance-sheet')
const reportDate = ref(new Date().toISOString().split('T')[0])
const startDate = ref(new Date(new Date().getFullYear(), 0, 1).toISOString().split('T')[0])
const endDate = ref(new Date().toISOString().split('T')[0])

const handleTabChange = (tab) => {
  activeTab.value = tab
}
</script>

<style scoped>
.financial-reports-container {
  padding: 20px;
}
</style>