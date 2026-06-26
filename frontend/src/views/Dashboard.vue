<template>
  <div class="dashboard">
    <!-- 4 大屏卡片 -->
    <el-row :gutter="20" v-loading="loading">
      <el-col :xs="24" :sm="12" :lg="6" class="card-col">
        <BossCard
          icon="TrendCharts"
          title="月度损益速览"
          accent-color="#409EFF"
          :main-value="profitLoss.net_profit"
          main-unit="净利润"
          :loading="loading"
          :items="[
            { label: '收入', value: profitLoss.total_revenue },
            { label: '成本', value: profitLoss.total_cost },
            { label: '毛利', value: profitLoss.gross_profit },
            { label: '费用', value: profitLoss.total_expenses },
            { label: '销售笔数', value: `${profitLoss.sale_count} 笔` }
          ]"
        />
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6" class="card-col">
        <BossCard
          icon="Box"
          title="库存资金占用"
          accent-color="#67C23A"
          :main-value="inventory.total_stock_value"
          main-unit="库存总值"
          :loading="loading"
          :items="[
            { label: '库存总量', value: `${inventory.total_quantity} 件` },
            { label: '商品种类', value: `${inventory.product_count} 种` },
            { label: '预警商品', value: `${inventory.low_stock_count} 个`, warning: inventory.low_stock_count > 0 },
            { label: '负库存', value: `${inventory.negative_stock_count} 件`, warning: inventory.negative_stock_count > 0 }
          ]"
        />
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6" class="card-col">
        <BossCard
          icon="Wallet"
          title="应收应付汇总"
          accent-color="#E6A23C"
          :main-value="receivable.total_receivable"
          main-unit="应收总额"
          :loading="loading"
          :items="[
            { label: '未回款客户', value: `${receivable.unpaid_customer_count} 家`, warning: receivable.unpaid_customer_count > 0 },
            { label: '应付总额', value: receivable.total_payable },
            { label: '未付供应商', value: `${receivable.unpaid_supplier_count} 家`, warning: receivable.unpaid_supplier_count > 0 },
          ]"
        />
      </el-col>
      <el-col :xs="24" :sm="12" :lg="6" class="card-col">
        <BossCard
          icon="Document"
          title="税务速算"
          accent-color="#9B59B6"
          :main-value="tax.total_tax"
          main-unit="本期预估税费"
          :loading="loading"
          :items="[
            { label: '增值税', value: tax.vat_payable },
            { label: '所得税', value: tax.income_tax_payable },
            { label: '所属期', value: tax.period_label },
          ]"
        />
      </el-col>
    </el-row>

    <!-- 趋势图表 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="24">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span class="section-title">趋势分析</span>
              <el-radio-group v-model="trendDays" size="small" @change="loadTrend">
                <el-radio-button :value="7">近7天</el-radio-button>
                <el-radio-button :value="30">近30天</el-radio-button>
                <el-radio-button :value="90">近90天</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <v-chart :option="trendOption" autoresize style="height: 300px;" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 库存预警 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="24">
        <el-card shadow="never">
          <template #header>
            <div class="card-header">
              <span class="section-title">库存预警</span>
              <el-badge v-if="alerts.length > 0" :value="alerts.length" type="warning" />
            </div>
          </template>
          <el-table v-if="alerts.length" :data="alerts" size="small" max-height="260" style="width:100%">
            <el-table-column prop="product_name" label="商品" />
            <el-table-column prop="product_sku" label="编码" width="120" />
            <el-table-column label="库存" width="100">
              <template #default="{ row }">
                <span :class="{
                  'negative-stock': row.quantity < 0,
                  'alert-stock': row.quantity >= 0 && row.quantity < row.min_stock
                }">{{ row.quantity }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="min_stock" label="预警线" width="80" />
          </el-table>
          <el-empty v-else description="暂无预警" :image-size="60" />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import BossCard from '../components/BossCard.vue'
import { useDashboardData } from '../composables/useDashboardData'
import { useAccountAwareData } from '../composables/useAccountAwareData'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])
const CHART_COLOR_PRIMARY = '#409EFF'
const CHART_COLOR_WARNING = '#E6A23C'

const {
  loading, profitLoss, inventory, receivable, tax,
  alerts, trendData, trendDays, loadAll, loadTrend
} = useDashboardData()

const trendOption = computed(() => {
  const d = trendData.value
  if (!d || !d.length) return {}
  const dates = d.map(v => {
    const parts = v.date ? v.date.split('-') : []
    return parts.length >= 3 ? `${parts[1]}/${parts[2]}` : v.date
  })
  const purchases = d.map(v => v.purchase_amount ?? 0)
  const sales = d.map(v => v.sale_amount ?? 0)
  return {
    tooltip: {
      trigger: 'axis',
      formatter(params) {
        const idx = params[0].dataIndex
        const date = d[idx]?.date || ''
        let s = `<b>${date}</b><br/>`
        for (const p of params) {
          s += `${p.marker} ${p.seriesName}: ¥${Number(p.value).toLocaleString()}<br/>`
        }
        return s
      }
    },
    legend: { data: ['采购金额', '销售金额'], bottom: 0 },
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: dates },
    yAxis: {
      type: 'value',
      axisLabel: { formatter: val => val >= 10000 ? (val / 10000).toFixed(1) + '万' : val }
    },
    series: [
      {
        name: '采购金额', type: 'line', data: purchases,
        smooth: true, itemStyle: { color: CHART_COLOR_WARNING },
        areaStyle: { color: 'rgba(230,162,60,0.08)' }
      },
      {
        name: '销售金额', type: 'line', data: sales,
        smooth: true, itemStyle: { color: CHART_COLOR_PRIMARY },
        areaStyle: { color: 'rgba(64,158,255,0.08)' }
      }
    ]
  }
})

useAccountAwareData(loadAll)
</script>

<style scoped>
.dashboard {
  animation: fadeIn 0.4s ease-out;
}
@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
.card-col {
  margin-bottom: 20px;
}
.section-title {
  font-weight: 600;
  font-size: 15px;
}
</style>
