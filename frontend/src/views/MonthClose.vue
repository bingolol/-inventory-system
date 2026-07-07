<template>
  <div>
    <div class="row">
      <div class="c4"><div class="stat-mini"><span class="stat-mini-label">月结期间</span><span class="stat-mini-value" style="font-size:22px;color:var(--primary);">{{ period }}</span></div></div>
      <div class="c4"><div class="stat-mini"><span class="stat-mini-label">月结状态</span><span class="stat-mini-value" :style="{ color: closedMonths.includes(period) ? 'var(--text-placeholder)' : 'var(--warning)' }">{{ closedMonths.includes(period) ? '已月结' : '未月结' }}</span></div></div>
      <div class="c4"><div class="stat-mini"><span class="stat-mini-label">操作</span><span style="font-size:13px;color:var(--text-secondary);display:block;margin-top:8px;">月结后数据锁定，不可逆</span></div></div>
    </div>

    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">期末处理</span>
          <div class="card-header-actions">
            <el-date-picker v-model="period" type="month" value-format="YYYY-MM" style="width:160px;" placeholder="选择月份" @change="checkStatus" />
            <el-button type="danger" @click="handleMonthClose" :loading="monthClosing" :disabled="closedMonths.includes(period)">执行月结</el-button>
          </div>
        </div>
      </template>

      <div class="info-box">
        <div class="info-title">月结将自动完成以下操作</div>
        <div class="info-steps">
          <div class="info-step"><span class="info-num">1</span><span>计提固定资产折旧</span></div>
          <div class="info-step"><span class="info-num">2</span><span>计算当月增值税（销项-进项）</span></div>
          <div class="info-step"><span class="info-num">3</span><span>计提城市维护建设税和教育费附加（增值税×12%）</span></div>
          <div class="info-step"><span class="info-num">4</span><span>计提企业所得税（应纳税所得额×税率）</span></div>
          <div class="info-step"><span class="info-num">5</span><span>结转损益至本年利润</span></div>
        </div>
      </div>

      <div v-if="lastResult" class="result-box">
        <div class="result-title">上次月结结果 ({{ lastPeriod }})</div>
        <div class="result-grid">
          <div class="result-item"><span class="result-label">折旧笔数</span><span class="result-value">{{ lastResult.depreciation_count ?? '-' }}</span></div>
          <div class="result-item"><span class="result-label">当前增值税</span><span class="result-value">¥{{ formatMoney(lastResult.curr_vat) }}</span></div>
          <div class="result-item"><span class="result-label">所得税</span><span class="result-value">¥{{ formatMoney(lastResult.target_income_tax) }}</span></div>
          <div class="result-item"><span class="result-label">附加税</span><span class="result-value">¥{{ formatMoney(lastResult.surcharge) }}</span></div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import financeApi from '../api/finance'
import { formatMoney } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../utils/errorHandler'

const period = ref(new Date().toISOString().slice(0, 7))
const monthClosing = ref(false)
const closedMonths = ref([])
const lastResult = ref(null)
const lastPeriod = ref('')

const checkStatus = () => {
  // 月份变更时更新月结状态显示
}

const handleMonthClose = async () => {
  if (!period.value) { ElMessage.warning('请先选择月结期间'); return }
  try {
    await ElMessageBox.confirm(`确认执行 ${period.value} 月结？\n\n月结后该期间数据将被锁定，不可逆。\n请确认：\n1. 所有采购/销售单据已录入\n2. 银行对账已完成\n3. 所有发票已认证`, '月结确认', { confirmButtonText: '执行月结', cancelButtonText: '取消', type: 'warning' })
  } catch { return }
  monthClosing.value = true
  try {
    const res = await financeApi.monthClose(period.value)
    const data = res?.entity || res
    ElMessage.success(`${period.value} 月结完成`)
    lastResult.value = data
    lastPeriod.value = period.value
    if (!closedMonths.value.includes(period.value)) closedMonths.value.push(period.value)
    let msg = ''
    if (data.curr_vat !== undefined) msg += `\n当前增值税: ¥${data.curr_vat}`
    if (data.target_income_tax !== undefined) msg += `\n所得税: ¥${data.target_income_tax}`
    if (data.surcharge !== undefined) msg += `\n附加税: ¥${data.surcharge}`
    if (data.depreciation_count !== undefined) msg += `\n折旧: ${data.depreciation_count}项`
    if (msg) ElMessage.info(`月结详情:${msg}`, 6000)
  } catch (e) { handleError(e, { defaultMsg: '月结失败，请检查该期间是否已月结或存在未处理事务' }) }
  finally { monthClosing.value = false }
}
</script>

<style scoped>
.row { display:flex; gap:16px; margin-bottom:20px; }
.c4 { flex:1; }
.stat-mini { background:var(--bg-card); border:1px solid var(--border-light); border-left:4px solid var(--primary); border-radius:12px; padding:16px 20px; }
.stat-mini-label { display:block; font-size:13px; color:var(--text-secondary); font-weight:500; margin-bottom:4px; }
.stat-mini-value { font-size:26px; font-weight:700; letter-spacing:-0.5px; }

.info-box { background:var(--bg-elevated); border:1px solid var(--border-lighter); border-radius:12px; padding:20px; margin-bottom:16px; }
.info-title { font-size:14px; font-weight:600; color:var(--text-primary); margin-bottom:12px; }
.info-steps { display:flex; flex-direction:column; gap:8px; }
.info-step { display:flex; align-items:center; gap:10px; font-size:13px; color:var(--text-regular); }
.info-num { width:22px; height:22px; border-radius:50%; background:var(--primary-light); color:var(--primary); font-size:12px; font-weight:700; display:flex; align-items:center; justify-content:center; flex-shrink:0; }

.result-box { background:var(--bg-elevated); border:1px solid var(--border-lighter); border-radius:12px; padding:20px; }
.result-title { font-size:14px; font-weight:600; color:var(--text-primary); margin-bottom:12px; }
.result-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:12px; }
.result-item { background:var(--bg-card); border-radius:8px; padding:12px; text-align:center; }
.result-label { display:block; font-size:11px; color:var(--text-secondary); margin-bottom:4px; }
.result-value { font-size:18px; font-weight:700; color:var(--text-primary); font-family:var(--font-mono); }
</style>
