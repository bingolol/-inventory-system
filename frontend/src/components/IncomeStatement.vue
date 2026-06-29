<template>
  <div>
    <div class="is-top">
      <el-date-picker v-model="s" type="date" placeholder="开始日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" @change="load" style="width:150px" />
      <span style="color:var(--text-secondary);">至</span>
      <el-date-picker v-model="e" type="date" placeholder="结束日期" format="YYYY-MM-DD" value-format="YYYY-MM-DD" @change="load" style="width:150px" />
      <el-button type="primary" @click="load" :loading="loading">查询</el-button>
    </div>

    <div v-if="d" class="is-body">
      <div class="is-hero">
        <div>
          <div class="is-hero-title">利润表</div>
          <div class="is-hero-period">{{ formatDate(s) }} ~ {{ formatDate(e) }}</div>
        </div>
        <div class="is-hero-result">
          <div class="is-hero-label">净利润</div>
          <div class="is-hero-value" :style="{ color: d.net_profit >= 0 ? 'var(--success)' : 'var(--danger)' }">{{ formatMoney(d.net_profit) }}</div>
        </div>
      </div>

      <div class="is-cards">
        <div class="is-card">
          <div class="is-card-header c-primary">营业收入</div>
          <div class="is-card-value c-primary">{{ formatMoney(d.revenue) }}</div>
          <div class="is-card-formula">本月已完成的销售订单金额合计</div>
        </div>

        <div class="is-card">
          <div class="is-card-header c-warning">营业成本</div>
          <div class="is-card-value c-warning">{{ formatMoney(d.cost_of_goods_sold) }}</div>
          <div class="is-card-formula">已售商品的成本合计</div>
        </div>

        <div class="is-card is-card-hl">
          <div class="is-card-header">毛利润</div>
          <div class="is-card-value">{{ formatMoney(d.gross_profit) }}</div>
          <div class="is-card-formula">营业收入 − 营业成本 = 毛利润</div>
        </div>
      </div>

      <div class="is-breakdown">
        <div class="is-breakdown-title">费用明细</div>
        <div class="is-breakdown-cols">
          <div class="is-bd-item"><span class="is-bd-label">销售费用</span><span class="is-bd-value">{{ formatMoney(d.selling_expenses) }}</span></div>
          <div class="is-bd-item"><span class="is-bd-label">管理费用</span><span class="is-bd-value">{{ formatMoney(d.administrative_expenses) }}</span></div>
          <div class="is-bd-item"><span class="is-bd-label">财务费用</span><span class="is-bd-value">{{ formatMoney(d.financial_expenses) }}</span></div>
          <div class="is-bd-item is-bd-total"><span class="is-bd-label">费用合计</span><span class="is-bd-value">{{ formatMoney(d.total_operating_expenses) }}</span></div>
        </div>
      </div>

      <div class="is-formula-chain">
        <div class="is-fc-step">
          <div class="is-fc-expr">毛利润 − 费用合计 = 营业利润</div>
          <div class="is-fc-num">{{ formatMoney(d.gross_profit) }} − {{ formatMoney(d.total_operating_expenses) }} = <strong>{{ formatMoney(d.operating_profit) }}</strong></div>
        </div>
        <div class="is-fc-step" v-if="d.non_operating_income || d.non_operating_expense">
          <div class="is-fc-expr">营业利润 + 营业外收入 − 营业外支出 = 利润总额</div>
          <div class="is-fc-num">{{ formatMoney(d.operating_profit) }} + {{ formatMoney(d.non_operating_income) }} − {{ formatMoney(d.non_operating_expense) }} = <strong>{{ formatMoney(d.gross_profit_total) }}</strong></div>
        </div>
        <div class="is-fc-step">
          <div class="is-fc-expr">利润总额 − 所得税费用 = 净利润</div>
          <div class="is-fc-num">{{ formatMoney(d.gross_profit_total) }} − {{ formatMoney(d.income_tax_expense) }} = <strong>{{ formatMoney(d.net_profit) }}</strong></div>
        </div>
      </div>
    </div>
    <div v-else style="padding:40px 0;"><el-empty description="暂无数据，请先录入业务数据" /></div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import financeApi from '../api/finance'
import { formatMoney, formatDate } from '../utils/format'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../utils/errorHandler'

const props = defineProps({
  startDate: { type: String, default: () => new Date(new Date().getFullYear(), 0, 1).toISOString().split('T')[0] },
  endDate: { type: String, default: () => new Date().toISOString().split('T')[0] }
})
const loading = ref(false)
const d = ref(null)
const s = ref(props.startDate)
const e = ref(props.endDate)

watch(() => [props.startDate, props.endDate], ([ns, ne]) => { s.value = ns; e.value = ne; load() })
const load = async () => {
  loading.value = true
  try { d.value = await financeApi.getIncomeStatement(s.value, e.value) }
  catch (err) { handleError(err, { defaultMsg: '加载利润表失败，请检查本期是否有已完成销售订单' }); d.value = null }
  finally { loading.value = false }
}
useAccountAwareData(load)
</script>

<style scoped>
.is-top { display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
.is-body { animation: if2 0.3s ease; }
@keyframes if2 { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

.is-hero {
  background: linear-gradient(135deg, #1a1a2e, #16213e);
  border-radius: 14px; padding: 20px 24px; color: var(--bg-card);
  display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 20px;
}
.is-hero-title { font-size: 20px; font-weight: 700; }
.is-hero-period { font-size: 13px; color: rgba(255,255,255,0.4); margin-top: 4px; }
.is-hero-result { text-align: right; }
.is-hero-label { font-size: 12px; color: rgba(255,255,255,0.4); display: block; margin-bottom: 2px; }
.is-hero-value { font-size: 28px; font-weight: 800; letter-spacing: -1px; }

.is-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-bottom: 16px; }
.is-card { background: var(--bg-elevated); border: 1px solid var(--border-lighter); border-radius: 12px; padding: 16px; }
.is-card-hl { background: var(--primary-light); border-color: var(--border-light); }
.is-card-header { font-size: 13px; font-weight: 600; color: var(--text-primary); margin-bottom: 6px; }
.is-card-value { font-size: 22px; font-weight: 700; margin-bottom: 6px; font-family: 'Consolas', 'Monaco', monospace; }
.is-card-formula { font-size: 12px; color: var(--text-secondary); }

.is-breakdown { margin-bottom: 16px; }
.is-breakdown-title { font-size: 14px; font-weight: 600; color: var(--text-primary); margin-bottom: 8px; }
.is-breakdown-cols { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; }
.is-bd-item {
  background: var(--bg-elevated); border: 1px solid var(--border-lighter); border-radius: 8px;
  padding: 10px 12px; display: flex; flex-direction: column; gap: 4px;
}
.is-bd-label { font-size: 12px; color: var(--text-secondary); }
.is-bd-value { font-size: 16px; font-weight: 700; color: var(--danger); font-family: 'Consolas', 'Monaco', monospace; }
.is-bd-total { background: var(--danger-light); border-color: #fce4e4; }
.is-bd-total .is-bd-value { font-size: 18px; }

.is-formula-chain { display: flex; flex-direction: column; gap: 8px; }
.is-fc-step {
  background: var(--bg-card); border: 1px solid var(--border-lighter); border-radius: 10px;
  padding: 14px 16px; box-shadow: 0 1px 4px rgba(0,0,0,0.02);
}
.is-fc-expr { font-size: 13px; color: var(--text-secondary); margin-bottom: 4px; font-family: 'Consolas', 'Monaco', monospace; }
.is-fc-num { font-size: 15px; color: var(--text-regular); font-family: 'Consolas', 'Monaco', monospace; }
.is-fc-num strong { color: var(--primary); font-size: 17px; }
</style>
