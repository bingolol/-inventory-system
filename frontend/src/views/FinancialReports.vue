<template>
  <div class="financial-reports-container">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">财务报表</span>
          <div>
            <span style="font-size:12px;color:var(--text-placeholder);margin-right:8px;">月结期间</span>
            <el-date-picker v-model="monthClosePeriod" type="month" value-format="YYYY-MM" style="width:140px;" />
            <el-button type="danger" size="small" @click="handleMonthClose" :loading="monthClosing">执行月结</el-button>
          </div>
        </div>
      </template>

      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <el-tab-pane label="资产负债表" name="balance-sheet">
          <BalanceSheet :date="reportDate" />
        </el-tab-pane>
        <el-tab-pane label="利润表" name="income-statement">
          <IncomeStatement :start-date="startDate" :end-date="endDate" />
        </el-tab-pane>
        <el-tab-pane label="期初余额" name="opening-balance">
          <OpeningBalanceTab />
        </el-tab-pane>
<<<<<<< Updated upstream
=======
        <el-tab-pane label="小企业会计准则报表" name="cwbb-xqykjzz">
          <CWBBXQYKJZZ :date="reportDate" />
        </el-tab-pane>
>>>>>>> Stashed changes
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import financeApi from '../api/finance'
import BalanceSheet from '../components/BalanceSheet.vue'
import IncomeStatement from '../components/IncomeStatement.vue'
import OpeningBalanceTab from '../components/OpeningBalanceTab.vue'
<<<<<<< Updated upstream
=======
import CWBBXQYKJZZ from '../components/CWBBXQYKJZZ.vue'
>>>>>>> Stashed changes
import { handleError } from '../utils/errorHandler'

const activeTab = ref('income-statement')
const reportDate = ref(new Date().toISOString().split('T')[0])
const startDate = ref(new Date(new Date().getFullYear(), 0, 1).toISOString().split('T')[0])
const endDate = ref(new Date().toISOString().split('T')[0])
const monthClosePeriod = ref(new Date().toISOString().slice(0, 7))
const monthClosing = ref(false)

const handleTabChange = (tab) => {
  activeTab.value = tab
}

const handleMonthClose = async () => {
  if (!monthClosePeriod.value) { ElMessage.warning('请先选择月结期间'); return }
  try {
    await ElMessageBox.confirm(`确认执行 ${monthClosePeriod.value} 月结？\n月结将：\n1. 自动计提固定资产折旧\n2. 计算当月增值税\n3. 计提附加税\n4. 计提企业所得税\n5. 结转损益\n\n月结后该期间数据将被锁定，请确认所有业务已录入完毕。`, '月结确认', { confirmButtonText: '执行月结', cancelButtonText: '取消', type: 'warning' })
  } catch {
    return
  }
  monthClosing.value = true
  try {
    const res = await financeApi.monthClose(monthClosePeriod.value)
    const data = res?.entity || res
    ElMessage.success(`${monthClosePeriod.value} 月结完成`)
    let msg = ''
    if (data.curr_vat !== undefined) msg += `\n当前增值税: ¥${data.curr_vat}`
    if (data.target_income_tax !== undefined) msg += `\n所得税: ¥${data.target_income_tax}`
    if (data.surcharge !== undefined) msg += `\n附加税: ¥${data.surcharge}`
    if (data.depreciation_count !== undefined) msg += `\n折旧: ${data.depreciation_count}项`
    if (msg) ElMessage.info(`月结详情:${msg}`, 6000)
    window.location.reload()
  } catch (e) { handleError(e, { defaultMsg: '月结失败，请检查该期间是否已月结或存在未处理事务' }) }
  finally { monthClosing.value = false }
}
</script>

<style scoped>
.financial-reports-container {
  padding: 0;
}
</style>
