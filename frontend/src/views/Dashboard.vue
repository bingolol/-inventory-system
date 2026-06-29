<template>
  <div class="d" v-loading="loading">
    <!-- Row 1: 4 metrics -->
    <div class="d-row">
      <div class="d-c">
        <div class="d-ct">
          <span class="d-cl">本月净利润</span>
          <span class="d-bdg" :class="profitLoss.net_profit > 0 ? 'd-bdg-su' : 'd-bdg-da'" v-if="profitLoss.net_profit !== 0">
            {{ profitLoss.net_profit > 0 ? '盈利' : '亏损' }}
          </span>
        </div>
        <div class="d-cv" :style="{ color: profitLoss.net_profit >= 0 ? 'var(--success)' : 'var(--danger)' }">{{ formatMoney(profitLoss.net_profit) }}</div>
        <div class="d-divider"></div>
        <div class="d-ci"><span class="d-cil">收入</span><span class="d-civ">{{ formatMoney(profitLoss.total_revenue) }}</span></div>
        <div class="d-ci"><span class="d-cil">成本</span><span class="d-civ">{{ formatMoney(profitLoss.total_cost) }}</span></div>
        <div class="d-ci"><span class="d-cil">费用</span><span class="d-civ">{{ formatMoney(profitLoss.total_expenses) }}</span></div>
        <div class="d-ci"><span class="d-cil">毛利</span><span class="d-civ">{{ formatMoney(profitLoss.total_revenue - profitLoss.total_cost) }}</span></div>
      </div>
      <div class="d-c">
        <div class="d-cl">别人欠我</div>
        <div class="d-cv" style="color:var(--primary);">{{ formatMoney(receivable.total_receivable) }}</div>
        <div class="d-divider"></div>
        <div class="d-ci"><span class="d-cil">未回款客户</span><span class="d-civ">{{ receivable.unpaid_customer_count }} 家</span></div>
        <div class="d-ci"><span class="d-cil">销售笔数</span><span class="d-civ">{{ profitLoss.sale_count }}</span></div>
      </div>
      <div class="d-c">
        <div class="d-cl">我欠别人</div>
        <div class="d-cv" style="color:var(--danger);">{{ formatMoney(receivable.total_payable) }}</div>
        <div class="d-divider"></div>
        <div class="d-ci"><span class="d-cil">未付供应商</span><span class="d-civ">{{ receivable.unpaid_supplier_count }} 家</span></div>
      </div>
      <div class="d-c">
        <div class="d-cl">库存资金</div>
        <div class="d-cv" style="color:var(--warning);">{{ formatMoney(inventory.total_stock_value) }}</div>
        <div class="d-divider"></div>
        <div class="d-ci"><span class="d-cil">库存总量</span><span class="d-civ">{{ inventory.total_quantity }} 件</span></div>
        <div class="d-ci"><span class="d-cil">商品种类</span><span class="d-civ">{{ inventory.product_count }} 种</span></div>
        <div class="d-ci"><span class="d-cil">预警项</span><span class="d-civ" :style="{ color: inventory.low_stock_count > 0 ? 'var(--danger)' : 'var(--text-secondary)' }">{{ inventory.low_stock_count }}</span></div>
      </div>
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
            <div class="d-fstep" @click="router.push('/supply-chain')"><span class="d-ficon" style="background:var(--success-light);">📦</span><span class="d-fname">采购入库</span></div>
            <span class="d-farrow">→</span>
            <div class="d-fstep" @click="router.push('/sales-customers')"><span class="d-ficon" style="background:var(--primary-light);">📋</span><span class="d-fname">销售开单</span></div>
            <span class="d-farrow">→</span>
            <div class="d-fstep" @click="router.push('/expenses')"><span class="d-ficon" style="background:var(--danger-light);">💸</span><span class="d-fname">费用/付款</span></div>
            <span class="d-farrow">→</span>
            <div class="d-fstep" @click="router.push('/invoices')"><span class="d-ficon" style="background:var(--warning-light);">🧾</span><span class="d-fname">录发票</span></div>
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
              <td style="color:var(--text-placeholder);">{{ a.product_sku }}</td>
              <td :style="{ color: a.quantity < 0 ? 'var(--danger)' : 'var(--warning)', fontWeight:600 }">{{ a.quantity }}</td>
              <td><span class="d-bg" :class="a.quantity < 0 ? 'd-bd' : 'd-bw'">{{ a.quantity < 0 ? '负库存' : '低于预警线' }}</span></td>
            </tr>
          </table>
          <div v-else style="padding:16px 0;text-align:center;color:var(--text-placeholder);font-size:13px;">暂无预警，库存状况良好</div>
        </div>
      </div>

      <div class="d-side">
        <div class="d-box" style="height:100%;">
          <div class="d-bh"><span class="d-bt">收入趋势</span><span style="font-size:11px;color:var(--text-placeholder);">近30天</span></div>
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
    xAxis: { type: 'category', data: d.map(v => { const x = v.date?.split('-'); return x?.length >= 3 ? `${x[1]}/${x[2]}` : v.date }), axisLabel: { fontSize: 9, color: '#b7b5a9' }, axisLine: { lineStyle: { color: '#3d3d3a' } } },
    yAxis: { type: 'value', splitLine: { lineStyle: { color: '#3d3d3a' } }, axisLabel: { fontSize: 9, color: '#b7b5a9' } },
    series: [
      { name: '销售', type: 'line', smooth: true, data: d.map(v => v.sale_amount ?? 0), lineStyle: { color: '#d97757', width: 2 }, areaStyle: { color: 'rgba(217,119,87,0.08)' }, symbol: 'none' },
      { name: '采购', type: 'line', smooth: true, data: d.map(v => v.purchase_amount ?? 0), lineStyle: { color: '#9c87f5', width: 2 }, areaStyle: { color: 'rgba(156,135,245,0.08)' }, symbol: 'none' }
    ]
  }
})

useAccountAwareData(loadAll)
</script>

<style scoped>
.d { animation: df 0.2s ease; }
@keyframes df { from { opacity: 0; } to { opacity: 1; } }

.d-row { display: flex; gap: 16px; margin-bottom: 20px; }
.d-c { flex: 1; background: var(--bg-card); border: 1px solid var(--border-light); border-left: 4px solid var(--primary); border-radius: 12px; padding: 18px 20px; display: flex; flex-direction: column; gap: 0; }
.d-ct { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.d-cl { font-size: 13px; color: var(--primary); font-weight: 700; letter-spacing: 0.3px; text-transform: uppercase; font-size: 11px; }
.d-bdg { font-size: 11px; padding: 2px 8px; border-radius: 8px; font-weight: 600; }
.d-bdg-su { background: var(--success-light); color: var(--success); }
.d-bdg-da { background: var(--danger-light); color: var(--danger); }
.d-cv { font-size: 28px; font-weight: 700; letter-spacing: -0.5px; line-height: 1.1; margin-bottom: 0; font-family: var(--font-mono); }
.d-divider { height: 1px; background: var(--border-light); margin: 8px 0 6px; }
.d-ci { display: flex; justify-content: space-between; align-items: center; padding: 2px 0; font-size: 13px; line-height: 1.6; }
.d-cil { color: var(--text-secondary); }
.d-civ { font-weight: 600; color: var(--text-regular); font-family: var(--font-mono); }

.d-main { flex: 1; display: flex; flex-direction: column; gap: 12px; }
.d-side { flex: 0 0 360px; }
.d-box { background: var(--bg-card); border: 1px solid var(--border-lighter); border-radius: 12px; padding: 16px; }
.d-bh { display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }
.d-bt { font-size: 13px; font-weight: 600; color: var(--text-primary); }
.d-bl { font-size: 12px; color: var(--text-secondary); cursor: pointer; }
.d-bl:hover { color: var(--primary); }

.d-acts { display: flex; gap: 8px; flex-wrap: wrap; }

/* Summary grid */
.d-summary { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
.d-si { background: var(--bg-elevated); border-radius: 8px; padding: 8px 10px; display: flex; flex-direction: column; gap: 2px; }
.d-sil { font-size: 11px; color: var(--text-secondary); }
.d-siv { font-size: 18px; font-weight: 700; color: var(--text-primary); font-family: var(--font-mono); }
.d-btn { display: inline-flex; align-items: center; gap: 4px; padding: 6px 12px; border: 1px solid var(--border-lighter); border-radius: 8px; font-size: 12px; color: var(--text-regular); cursor: pointer; background: var(--bg-card); }
.d-btn:hover { background: var(--bg-hover); border-color: var(--border-light); }

/* Business flow */
.d-flow { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.d-fstep { display: flex; align-items: center; gap: 6px; padding: 6px 10px; border: 1px solid var(--border-lighter); border-radius: 8px; cursor: pointer; background: var(--bg-card); }
.d-fstep:hover { background: var(--bg-hover); }
.d-ficon { width: 24px; height: 24px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 14px; }
.d-fname { font-size: 12px; font-weight: 500; color: var(--text-primary); }
.d-farrow { color: var(--border-light); font-size: 14px; }

.d-tbl { width: 100%; border-collapse: collapse; }
.d-tbl th { text-align: left; padding: 8px 10px; font-size: 11px; font-weight: 600; color: var(--text-secondary); border-bottom: 1px solid var(--border-lighter); }
.d-tbl td { padding: 8px 10px; font-size: 13px; color: var(--text-regular); border-bottom: 1px solid var(--border-lighter); }
.d-tbl tr:last-child td { border: none; }
.d-tbl tr:hover td { background: var(--bg-hover); }

.d-bg { display: inline-block; padding: 1px 8px; border-radius: 8px; font-size: 11px; font-weight: 500; }
.d-bw { background: var(--warning-light); color: var(--warning); }
.d-bd { background: var(--danger-light); color: var(--danger); }
</style>
