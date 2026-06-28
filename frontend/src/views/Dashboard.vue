<template>
  <div class="d" v-loading="loading">
    <!-- Row 1: 4 metrics -->
    <div class="d-row">
      <div class="d-c">
        <div class="d-ct"><span class="d-cl">本月净利润</span><span class="d-cup" v-if="profitLoss.net_profit > 0">盈利</span></div>
        <div class="d-cv" :style="{ color: profitLoss.net_profit >= 0 ? '#67c23a' : '#f56c6c' }">{{ formatMoney(profitLoss.net_profit) }}</div>
        <div class="d-cs">收入 {{ formatMoney(profitLoss.total_revenue) }} — 成本 {{ formatMoney(profitLoss.total_cost) }} — 费用 {{ formatMoney(profitLoss.total_expenses) }}</div>
      </div>
      <div class="d-c"><div class="d-cl">别人欠我</div><div class="d-cv" style="color:#4f62c0;">{{ formatMoney(receivable.total_receivable) }}</div><div class="d-cs">{{ receivable.unpaid_customer_count }} 家客户未回款</div></div>
      <div class="d-c"><div class="d-cl">我欠别人</div><div class="d-cv" style="color:#f56c6c;">{{ formatMoney(receivable.total_payable) }}</div><div class="d-cs">{{ receivable.unpaid_supplier_count }} 家供应商</div></div>
      <div class="d-c"><div class="d-cl">库存资金</div><div class="d-cv" style="color:#e6a23c;">{{ formatMoney(inventory.total_stock_value) }}</div><div class="d-cs">{{ inventory.total_quantity }} 件 · {{ inventory.product_count }} 种 · {{ inventory.low_stock_count }} 项预警</div></div>
    </div>

    <!-- Row 2 -->
    <div class="d-row" style="flex:1;">
      <div class="d-main">
        <div class="d-box">
          <div class="d-bh"><span class="d-bt">业务概要</span></div>
          <div class="d-summary">
            <div class="d-si"><span class="d-sil">本月收入</span><span class="d-siv">{{ formatMoney(profitLoss.total_revenue) }}</span></div>
            <div class="d-si"><span class="d-sil">本月成本</span><span class="d-siv">{{ formatMoney(profitLoss.total_cost) }}</span></div>
            <div class="d-si"><span class="d-sil">本月费用</span><span class="d-siv">{{ formatMoney(profitLoss.total_expenses) }}</span></div>
            <div class="d-si"><span class="d-sil">销售笔数</span><span class="d-siv">{{ profitLoss.sale_count }}</span></div>
            <div class="d-si"><span class="d-sil">商品种类</span><span class="d-siv">{{ inventory.product_count }}</span></div>
            <div class="d-si"><span class="d-sil">库存总量</span><span class="d-siv">{{ inventory.total_quantity }}</span></div>
          </div>
          <div class="d-bh"><span class="d-bt">业务处理</span></div>
          <div class="d-flow">
            <div class="d-fstep" @click="router.push('/supply-chain')"><span class="d-ficon" style="background:#f0f9eb;">📦</span><span class="d-fname">采购入库</span></div>
            <span class="d-farrow">→</span>
            <div class="d-fstep" @click="router.push('/sales-customers')"><span class="d-ficon" style="background:#eef1ff;">📋</span><span class="d-fname">销售开单</span></div>
            <span class="d-farrow">→</span>
            <div class="d-fstep" @click="router.push('/expenses')"><span class="d-ficon" style="background:#fef0f0;">💸</span><span class="d-fname">费用/付款</span></div>
            <span class="d-farrow">→</span>
            <div class="d-fstep" @click="router.push('/invoices')"><span class="d-ficon" style="background:#fdf6ec;">🧾</span><span class="d-fname">录发票</span></div>
          </div>
          <div class="d-bh" style="margin-top:14px;"><span class="d-bt">数据查看</span></div>
          <div class="d-acts">
            <span class="d-btn" @click="router.push('/financial-overview')">📊 财务总览</span>
            <span class="d-btn" @click="router.push('/bank-accounts')">🏦 银行账户</span>
            <span class="d-btn" @click="router.push('/financial-reports')">📄 财务报表</span>
            <span class="d-btn" @click="router.push('/tax-report')">🏛️ 税务报表</span>
          </div>
        </div>

        <div class="d-box">
          <div class="d-bh"><span class="d-bt">库存预警</span><span class="d-bl" @click="router.push('/supply-chain')">全部 →</span></div>
          <table class="d-tbl" v-if="alerts.length">
            <tr><th>商品</th><th>编码</th><th style="width:60px;">库存</th><th style="width:90px;">状态</th></tr>
            <tr v-for="a in alerts.slice(0,5)" :key="a.product_id">
              <td style="font-weight:500;">{{ a.product_name }}</td>
              <td style="color:#c9cdd4;">{{ a.product_sku }}</td>
              <td :style="{ color: a.quantity < 0 ? '#f56c6c' : '#e6a23c', fontWeight:600 }">{{ a.quantity }}</td>
              <td><span class="d-bg" :class="a.quantity < 0 ? 'd-bd' : 'd-bw'">{{ a.quantity < 0 ? '负库存' : '低于预警线' }}</span></td>
            </tr>
          </table>
          <div v-else style="padding:16px 0;text-align:center;color:#c9cdd4;font-size:13px;">暂无预警，库存状况良好</div>
        </div>
      </div>

      <div class="d-side">
        <div class="d-box" style="height:100%;">
          <div class="d-bh"><span class="d-bt">收入趋势</span><span style="font-size:11px;color:#c9cdd4;">近30天</span></div>
          <v-chart :option="trendOption" autoresize style="height:calc(100% - 28px);min-height:240px;" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { useDashboardData } from '../composables/useDashboardData'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { formatMoney } from '../utils/format'

use([LineChart, GridComponent, TooltipComponent, CanvasRenderer])
const router = useRouter()
const { loading, profitLoss, inventory, receivable, alerts, trendData, loadAll } = useDashboardData()

const trendOption = computed(() => {
  const d = trendData.value
  if (!d?.length) return {}
  return {
    tooltip: { trigger: 'axis', formatter: (p) => `<b>${d[p[0].dataIndex]?.date || ''}</b><br/>${p.map(x => x.marker + ' ' + x.seriesName + ': ¥' + Number(x.value).toLocaleString()).join('<br/>')}` },
    grid: { left: 36, right: 8, top: 6, bottom: 24 },
    xAxis: { type: 'category', data: d.map(v => { const x = v.date?.split('-'); return x?.length >= 3 ? `${x[1]}/${x[2]}` : v.date }), axisLabel: { fontSize: 9, color: '#c9cdd4' } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#f5f5f5' } }, axisLabel: { fontSize: 9 } },
    series: [
      { name: '销售', type: 'line', smooth: true, data: d.map(v => v.sale_amount ?? 0), lineStyle: { color: '#4f62c0', width: 2 }, areaStyle: { color: 'rgba(79,98,192,0.05)' }, symbol: 'none' },
      { name: '采购', type: 'line', smooth: true, data: d.map(v => v.purchase_amount ?? 0), lineStyle: { color: '#e6a23c', width: 2 }, areaStyle: { color: 'rgba(230,162,60,0.05)' }, symbol: 'none' }
    ]
  }
})

useAccountAwareData(loadAll)
</script>

<style scoped>
.d { animation: df 0.2s ease; }
@keyframes df { from { opacity: 0; } to { opacity: 1; } }

.d-row { display: flex; gap: 12px; margin-bottom: 16px; }
.d-c { flex: 1; background: #fff; border: 1px solid #edf0f5; border-radius: 10px; padding: 16px; }
.d-ct { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px; }
.d-cl { font-size: 12px; color: #4e5969; font-weight: 500; }
.d-cup { font-size: 11px; padding: 1px 6px; border-radius: 4px; background: #f0f9eb; color: #67c23a; font-weight: 500; }
.d-cv { font-size: 26px; font-weight: 700; letter-spacing: -0.5px; line-height: 1.1; margin-bottom: 2px; }
.d-cs { font-size: 12px; color: #86909c; }

.d-main { flex: 1; display: flex; flex-direction: column; gap: 12px; }
.d-side { flex: 0 0 360px; }
.d-box { background: #fff; border: 1px solid #edf0f5; border-radius: 10px; padding: 16px; }
.d-bh { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.d-bt { font-size: 13px; font-weight: 600; color: #1d2129; }
.d-bl { font-size: 12px; color: #86909c; cursor: pointer; }
.d-bl:hover { color: #4f62c0; }

.d-acts { display: flex; gap: 8px; flex-wrap: wrap; }

/* Summary grid */
.d-summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.d-si { background: #f8f9fa; border-radius: 6px; padding: 8px 10px; display: flex; flex-direction: column; gap: 2px; }
.d-sil { font-size: 11px; color: #4e5969; }
.d-siv { font-size: 18px; font-weight: 700; color: #1d2129; font-family: 'Consolas','Monaco',monospace; }
.d-btn { display: inline-flex; align-items: center; gap: 4px; padding: 6px 12px; border: 1px solid #edf0f5; border-radius: 6px; font-size: 12px; color: #4e5969; cursor: pointer; background: #fff; }
.d-btn:hover { background: #f5f6f8; border-color: #d0d5dd; }

/* Business flow */
.d-flow { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.d-fstep { display: flex; align-items: center; gap: 6px; padding: 6px 10px; border: 1px solid #edf0f5; border-radius: 6px; cursor: pointer; background: #fff; }
.d-fstep:hover { background: #f5f6f8; }
.d-ficon { width: 24px; height: 24px; border-radius: 5px; display: flex; align-items: center; justify-content: center; font-size: 14px; }
.d-fname { font-size: 12px; font-weight: 500; color: #1d2129; }
.d-farrow { color: #d0d5dd; font-size: 14px; }

.d-tbl { width: 100%; border-collapse: collapse; }
.d-tbl th { text-align: left; padding: 8px 10px; font-size: 11px; font-weight: 600; color: #86909c; border-bottom: 1px solid #f5f6f8; }
.d-tbl td { padding: 8px 10px; font-size: 13px; color: #4e5969; border-bottom: 1px solid #f8f9fa; }
.d-tbl tr:last-child td { border: none; }
.d-tbl tr:hover td { background: #fafbfc; }

.d-bg { display: inline-block; padding: 1px 8px; border-radius: 4px; font-size: 11px; font-weight: 500; }
.d-bw { background: #fdf6ec; color: #e6a23c; }
.d-bd { background: #fef0f0; color: #f56c6c; }
</style>
