<template>
  <div v-loading="loading">
    <div class="box" style="margin-bottom:16px;">
      <div class="bh"><span class="bt">现金流量表</span></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap;">
        <el-date-picker v-model="q.startDate" type="date" placeholder="开始日期" value-format="YYYY-MM-DD" style="width:150px;" />
        <span style="color:#c9cdd4;line-height:32px;">至</span>
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
          <div class="cr" style="border-top:1px solid #f5f6f8;margin-top:4px;padding-top:4px;"><span style="font-weight:600;">净额</span><span class="cv-sm" :style="{ color: s.data.net>=0?'#4f62c0':'#f56c6c' }">{{ formatMoney(s.data.net) }}</span></div>
        </div>
      </div>
    </div>

    <div v-if="d" class="box" style="margin-bottom:16px;">
      <table class="tbl">
        <tr><th>项目</th><th style="width:140px;">金额</th></tr>
        <tr><td>净现金流量</td><td style="font-weight:700;">{{ formatMoney(d.net_cash_flow) }}</td></tr>
        <tr><td>期初余额</td><td>{{ formatMoney(d.beginning_cash_balance) }}</td></tr>
        <tr><td style="font-weight:600;">期末余额</td><td style="font-weight:700;color:#4f62c0;">{{ formatMoney(d.ending_cash_balance) }}</td></tr>
      </table>
    </div>

    <div class="box">
      <div class="bh"><span class="bt">现金流水</span></div>
      <table class="tbl" v-if="tx.length">
        <tr><th>日期</th><th style="width:60px;">类型</th><th style="width:120px;">金额</th><th>描述</th></tr>
        <tr v-for="t in tx" :key="t.id">
          <td>{{ formatDate(t.transaction_date) }}</td>
          <td><span class="bg" :class="t.type==='inflow'?'bs':'bd'">{{ t.type==='inflow'?'流入':'流出' }}</span></td>
          <td :style="{ color:t.type==='inflow'?'#67c23a':'#f56c6c', fontWeight:600 }">{{ t.type==='inflow'?'+':'-' }}{{ formatMoney(t.amount) }}</td>
          <td style="color:#86909c;">{{ t.description||'-' }}</td>
        </tr>
      </table>
      <div v-else style="padding:24px 0;text-align:center;color:#c9cdd4;font-size:13px;">暂无流水记录</div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, reactive } from 'vue'
import financeApi from '../api/finance'
import { formatMoney, formatDate } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../utils/errorHandler'

const q = reactive({ startDate: new Date(new Date().getFullYear(),0,1).toISOString().split('T')[0], endDate: new Date().toISOString().split('T')[0] })
const d = ref(null)
const tx = ref([])
const loading = ref(false)

const sections = computed(() => {
  const s = d.value
  if (!s) return []
  return [
    { title:'经营', color:'#4f62c0', data:s.operating_activities },
    { title:'投资', color:'#67c23a', data:s.investing_activities },
    { title:'筹资', color:'#e6a23c', data:s.financing_activities },
  ]
})

const load = async () => {
  loading.value = true
  try {
    d.value = await financeApi.getCashFlowStatement(q.startDate, q.endDate)
    const r = await financeApi.getCashFlowTransactions({ start_date:q.startDate, end_date:q.endDate, limit:100 }).catch(()=>({}))
    tx.value = r.items || []
  } catch (e) { handleError(e, { defaultMsg:'获取现金流量表失败' }) }
  finally { loading.value = false }
}

useAccountAwareData(load)
</script>

<style scoped>
.row { display:flex; gap:12px; }
.c4 { flex:1; }
.c { background:#fff; border:1px solid #edf0f5; border-radius:10px; padding:14px 16px; }
.cl { font-size:12px; color:#4e5969; font-weight:500; margin-bottom:8px; }
.cr { display:flex; justify-content:space-between; padding:2px 0; font-size:13px; color:#4e5969; }
.cv-sm { font-weight:600; font-family:'Consolas','Monaco',monospace; }

.box { background:#fff; border:1px solid #edf0f5; border-radius:10px; padding:16px; }
.bh { display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }
.bt { font-size:13px; font-weight:600; color:#1d2129; }

.tbl { width:100%; border-collapse:collapse; }
.tbl th { text-align:left; padding:8px 10px; font-size:11px; font-weight:600; color:#86909c; border-bottom:1px solid #f5f6f8; }
.tbl td { padding:8px 10px; font-size:13px; color:#4e5969; border-bottom:1px solid #f8f9fa; }
.tbl tr:last-child td { border:none; }

.bg { display:inline-block; padding:1px 8px; border-radius:4px; font-size:11px; font-weight:500; }
.bs { background:#f0f9eb; color:#67c23a; }
.bd { background:#fef0f0; color:#f56c6c; }

.c-success { color:#67c23a; }
.c-danger { color:#f56c6c; }
</style>
