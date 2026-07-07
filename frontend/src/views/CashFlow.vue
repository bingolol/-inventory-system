<template>
  <div v-loading="loading">
    <div class="box" style="margin-bottom:16px;">
      <div class="bh"><span class="bt">现金流量表</span>
        <el-button size="small" type="primary" @click="showCreateDialog">新增流水</el-button>
      </div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;">
        <el-date-picker v-model="q.startDate" type="date" placeholder="开始日期" value-format="YYYY-MM-DD" style="width:150px;" />
        <span style="color:var(--text-placeholder);line-height:32px;">至</span>
        <el-date-picker v-model="q.endDate" type="date" placeholder="结束日期" value-format="YYYY-MM-DD" style="width:150px;" />
        <el-button size="small" type="primary" @click="load">查询</el-button>
      </div>
    </div>

    <div v-if="d" class="row" style="margin-bottom:16px;">
      <div class="c4" v-for="s in sections" :key="s.title">
        <div class="c" :style="{ borderLeft:'3px solid '+s.color }">
          <div class="cl">{{ s.title }}</div>
          <div class="cr"><span>流入</span><span class="cv-sm c-success">{{ formatMoney(s.data.inflows) }}</span></div>
          <div class="cr"><span>流出</span><span class="cv-sm c-danger">{{ formatMoney(s.data.outflows) }}</span></div>
          <div class="cr" style="border-top:1px solid var(--border-lighter);margin-top:4px;padding-top:4px;"><span style="font-weight:600;">净额</span><span class="cv-sm" :style="{ color: s.data.net>=0?'var(--primary)':'var(--danger)' }">{{ formatMoney(s.data.net) }}</span></div>
        </div>
      </div>
    </div>

    <div v-if="d" class="box" style="margin-bottom:16px;">
      <table class="tbl">
        <tr><th>项目</th><th style="width:140px;">金额</th></tr>
        <tr><td>净现金流量</td><td style="font-weight:700;">{{ formatMoney(d.net_cash_flow) }}</td></tr>
        <tr><td>期初余额</td><td>{{ formatMoney(d.beginning_cash_balance) }}</td></tr>
        <tr><td style="font-weight:600;">期末余额</td><td style="font-weight:700;color:var(--primary);">{{ formatMoney(d.ending_cash_balance) }}</td></tr>
      </table>
    </div>

    <div class="box">
      <div class="bh"><span class="bt">现金流水</span></div>
      <table class="tbl" v-if="tx.length">
        <tr><th>日期</th><th style="width:60px;">类型</th><th style="width:120px;">金额</th><th>描述</th><th style="width:100px;">操作</th></tr>
        <tr v-for="t in tx" :key="t.id">
          <td>{{ formatDate(t.transaction_date) }}</td>
          <td><span class="bg" :class="t.type==='inflow'?'bs':'bd'">{{ t.type==='inflow'?'流入':'流出' }}</span></td>
          <td :style="{ color:t.type==='inflow'?'var(--success)':'var(--danger)', fontWeight:600 }">{{ t.type==='inflow'?'+':'-' }}{{ formatMoney(t.amount) }}</td>
          <td style="color:var(--text-secondary);">{{ t.description||'-' }}</td>
          <td>
            <el-popconfirm title="确定冲红此流水？" @confirm="handleReverse(t)">
              <template #reference><el-button size="small" link type="danger">冲红</el-button></template>
            </el-popconfirm>
          </td>
        </tr>
      </table>
      <div v-else style="padding:24px 0;text-align:center;color:var(--text-placeholder);font-size:13px;">暂无流水记录</div>
    </div>

    <el-dialog v-model="dialogVisible" title="新增现金流水" width="500px">
      <el-form :model="cfForm" label-width="0">
        <div class="fg" style="border-left-color:var(--primary);">
          <div class="fgh"><span class="fgt" style="background:var(--primary-light);color:var(--primary);">流水信息</span></div>
          <div class="fgb">
            <div class="ff"><span class="fl" style="min-width:70px;">日期</span><el-date-picker v-model="cfForm.transaction_date" type="date" value-format="YYYY-MM-DD" style="width:100%;" /></div>
            <div class="ff"><span class="fl" style="min-width:70px;">类型</span><el-select v-model="cfForm.type" style="width:100%"><el-option label="流入" value="inflow" /><el-option label="流出" value="outflow" /></el-select></div>
            <div class="ff"><span class="fl" style="min-width:70px;">金额</span><el-input-number v-model="cfForm.amount" :precision="2" :min="0" style="width:100%;" controls-position="right" /></div>
            <div class="ff"><span class="fl" style="min-width:70px;">分类</span><el-select v-model="cfForm.flow_category" style="width:100%"><el-option v-for="opt in enumsStore.flowCategoryOptions" :key="opt.value" :label="opt.label" :value="opt.value" /></el-select></div>
            <div class="ff"><span class="fl" style="min-width:70px;">描述</span><el-input v-model="cfForm.description" /></div>
          </div>
        </div>
      </el-form>
      <template #footer><el-button @click="dialogVisible=false">取消</el-button><el-button type="primary" @click="saveCashFlow">保存</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, reactive } from 'vue'
import { ElMessage } from 'element-plus'
import financeApi from '../api/finance'
import { formatMoney, formatDate } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../utils/errorHandler'
import { useEnumsStore } from '../stores/enums'

const enumsStore = useEnumsStore()

const q = reactive({ startDate: new Date(new Date().getFullYear(),0,1).toISOString().split('T')[0], endDate: new Date().toISOString().split('T')[0] })
const d = ref(null)
const tx = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const cfForm = ref({ transaction_date: '', type: 'inflow', amount: 0, flow_category: 'operating', description: '' })

const sections = computed(() => {
  const s = d.value
  if (!s) return []
  return [
    { title:'经营', color:'var(--primary)', data:s.operating_activities },
    { title:'投资', color:'var(--success)', data:s.investing_activities },
    { title:'筹资', color:'var(--warning)', data:s.financing_activities },
  ]
})

const load = async () => {
  loading.value = true
  try {
    d.value = await financeApi.getCashFlowStatement(q.startDate, q.endDate)
    try {
      const r = await financeApi.getCashFlowTransactions({ start_date:q.startDate, end_date:q.endDate, limit:100 })
      tx.value = r.items || []
    } catch (_) {
      tx.value = []
    }
  } catch (e) { handleError(e, { defaultMsg:'获取现金流量表失败' }) }
  finally { loading.value = false }
}

const showCreateDialog = () => {
  cfForm.value = { transaction_date: new Date().toISOString().slice(0, 10), type: 'inflow', amount: 0, flow_category: 'operating', description: '' }
  dialogVisible.value = true
}

const saveCashFlow = async () => {
  try {
    await financeApi.createCashFlowTransaction(cfForm.value)
    ElMessage.success('流水已创建')
    dialogVisible.value = false
    load()
  } catch (e) { handleError(e, { defaultMsg: '创建流水失败' }) }
}

const handleReverse = async (row) => {
  try {
    await financeApi.reverseCashFlowTransaction(row.id)
    ElMessage.success('流水已冲红')
    load()
  } catch (e) { handleError(e, { defaultMsg: '冲红失败' }) }
}

useAccountAwareData(load)
</script>

<style scoped>
.row { display:flex; gap:12px; }
.c4 { flex:1; }
.c { background:var(--bg-card); border:1px solid var(--border-lighter); border-radius:10px; padding:14px 16px; }
.cl { font-size:12px; color:var(--text-regular); font-weight:500; margin-bottom:8px; }
.cr { display:flex; justify-content:space-between; padding:2px 0; font-size:13px; color:var(--text-regular); }
.cv-sm { font-weight:600; font-family:'Consolas','Monaco',monospace; }
.box { background:var(--bg-card); border:1px solid var(--border-lighter); border-radius:10px; padding:16px; }
.bh { display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }
.bt { font-size:13px; font-weight:600; color:var(--text-primary); }
.tbl { width:100%; border-collapse:collapse; }
.tbl th { text-align:left; padding:8px 10px; font-size:11px; font-weight:600; color:var(--text-secondary); border-bottom:1px solid var(--border-lighter); }
.tbl td { padding:8px 10px; font-size:13px; color:var(--text-regular); border-bottom:1px solid var(--bg-elevated); }
.tbl tr:last-child td { border:none; }
.bg { display:inline-block; padding:1px 8px; border-radius:4px; font-size:11px; font-weight:500; }
.bs { background:var(--success-light); color:var(--success); }
.bd { background:var(--danger-light); color:var(--danger); }
.c-success { color:var(--success); }
.c-danger { color:var(--danger); }
.fg { background:var(--bg-elevated); border:1px solid var(--border-light); border-left:4px solid; border-radius:12px; overflow:hidden; }
.fgh { padding:12px 16px 4px; }
.fgt { display:inline-block; padding:2px 12px; border-radius:9999px; font-size:12px; font-weight:600; }
.fgb { padding:4px 16px 12px; display:flex; flex-direction:column; gap:10px; }
.ff { display:flex; align-items:center; gap:12px; }
.fl { font-size:13px; color:var(--text-regular); flex-shrink:0; }
</style>
