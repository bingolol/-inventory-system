<template>
  <div class="dashboard">
    <el-row :gutter="16" class="stat-row" v-loading="loading">
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon stat-icon--primary"><el-icon :size="28"><Goods /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ overview.total_products ?? 0 }}</div>
            <div class="stat-label">商品种类</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon stat-icon--success"><el-icon :size="28"><Box /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">{{ overview.total_inventory_quantity ?? 0 }}</div>
            <div class="stat-label">库存总量</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon stat-icon--warning"><el-icon :size="28"><ShoppingCart /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">¥{{ formatMoney(overview.today_purchase_amount ?? 0) }}</div>
            <div class="stat-label">今日采购 ({{ overview.today_purchase_count ?? 0 }}笔)</div>
          </div>
        </div>
      </el-col>
      <el-col :span="6">
        <div class="stat-card">
          <div class="stat-icon stat-icon--danger"><el-icon :size="28"><Sell /></el-icon></div>
          <div class="stat-info">
            <div class="stat-value">¥{{ formatMoney(overview.today_sale_amount ?? 0) }}</div>
            <div class="stat-label">今日销售 ({{ overview.today_sale_count ?? 0 }}笔)</div>
          </div>
        </div>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px;">
      <el-col :span="24">
        <el-card shadow="never">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span style="font-weight:600;">趋势分析</span>
              <el-radio-group v-model="trendDays" size="small" @change="loadTrend">
                <el-radio-button :value="7">近7天</el-radio-button>
                <el-radio-button :value="30">近30天</el-radio-button>
                <el-radio-button :value="90">近90天</el-radio-button>
              </el-radio-group>
            </div>
          </template>
          <v-chart :option="trendOption" autoresize style="height: 350px;" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" style="margin-top: 16px;">
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span style="font-weight:600;">库存预警</span>
              <el-badge v-if="overview.low_stock_count > 0" :value="overview.low_stock_count" type="warning" />
            </div>
          </template>
          <el-table v-if="alerts.length" :data="alerts" size="small" max-height="280" style="width:100%">
            <el-table-column prop="product_name" label="商品" />
            <el-table-column prop="product_sku" label="编码" width="100" />
            <el-table-column label="库存" width="80">
              <template #default="{ row }">
                <span :class="{ 'negative-stock': row.quantity < 0, 'alert-stock': row.quantity >= 0 && row.quantity < row.min_stock }">
                  {{ row.quantity }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="min_stock" label="预警线" width="70" />
          </el-table>
          <el-empty v-else description="暂无预警" :image-size="60" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>
            <span style="font-weight:600;">库存价值</span>
          </template>
          <div style="padding: 20px 0; text-align: center;">
            <div style="font-size: 36px; font-weight: 700; color: var(--primary);">
              ¥{{ formatMoney(overview.total_stock_value ?? 0) }}
            </div>
            <div style="color: var(--text-secondary); margin-top: 8px;">库存总价值（按进价计算）</div>
            <div v-if="overview.negative_stock_count > 0" style="color: var(--danger); margin-top: 8px; font-size: 13px;">
              ⚠️ 含负库存 {{ overview.negative_stock_count }} 件，未计入价值
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { ElMessage } from 'element-plus'
import productsApi from '../api/products'
import financeApi from '../api/finance'
import { formatMoney } from '../utils/format'
import { handleError } from '../api/index'
import { useAccountAwareData } from '../composables/useAccountAwareData'

// ECharts 颜色常量（Canvas 不支持 CSS 变量，须用 JS 常量）
const CHART_COLOR_WARNING = '#e6a23c'
const CHART_COLOR_DANGER = '#f56c6c'

use([LineChart, GridComponent, TooltipComponent, LegendComponent, CanvasRenderer])

const overview = ref({})
const loading = ref(false)
const alerts = ref([])
const trendData = ref([])
const trendDays = ref(7)

const trendOption = computed(() => {
  const dates = trendData.value.map(d => d.date.slice(5))
  const purchases = trendData.value.map(d => d.purchase_amount)
  const sales = trendData.value.map(d => d.sale_amount)
  return {
    tooltip: {
      trigger: 'axis',
      formatter(params) {
        const idx = params[0].dataIndex
        const date = trendData.value[idx]?.date || ''
        let s = `<b>${date}</b><br/>`
        for (const p of params) {
          s += `${p.marker} ${p.seriesName}: ¥${p.value.toLocaleString()}<br/>`
        }
        return s
      }
    },
    legend: { data: ['采购金额', '销售金额'], bottom: 0 },
    grid: { left: 50, right: 20, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: dates },
    yAxis: { type: 'value', axisLabel: { formatter: val => val >= 10000 ? (val / 10000).toFixed(1) + '万' : val } },
    series: [
      { name: '采购金额', type: 'line', data: purchases, smooth: true, itemStyle: { color: CHART_COLOR_WARNING }, areaStyle: { color: 'rgba(230,162,60,0.08)' } },
      { name: '销售金额', type: 'line', data: sales, smooth: true, itemStyle: { color: CHART_COLOR_DANGER }, areaStyle: { color: 'rgba(245,108,108,0.08)' } }
    ]
  }
})

const loadTrend = async () => {
  try {
    trendData.value = await financeApi.getTrend({ days: trendDays.value })
  } catch (e) {
    handleError(e, { feedback: 'silent' })
  }
}

const loadData = async () => {
  loading.value = true
  try {
    overview.value = await financeApi.getOverview()
  } catch (e) {
    handleError(e, { defaultMsg: '加载总览数据失败' })
  }
  try {
    alerts.value = await productsApi.getAlerts()
  } catch (e) {
    handleError(e, { feedback: 'silent' })
  }
  finally { loading.value = false }
}

useAccountAwareData(loadData, loadTrend)
</script>

<style scoped>
.dashboard {
  animation: fadeIn 0.4s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.stat-row .stat-card {
  display: flex;
  align-items: center;
  gap: 20px;
  background: linear-gradient(135deg, var(--bg-card) 0%, var(--bg-elevated) 100%);
  border: 1px solid var(--border-lighter);
  box-shadow: var(--shadow-sm);
  transition: all var(--transition-base);
  position: relative;
  overflow: hidden;
}

.stat-row .stat-card::after {
  content: '';
  position: absolute;
  top: -50%;
  right: -50%;
  width: 100%;
  height: 100%;
  background: radial-gradient(circle, var(--primary-glow) 0%, transparent 70%);
  opacity: 0;
  transition: opacity var(--transition-slow);
}

.stat-row .stat-card:hover::after {
  opacity: 1;
}

.stat-icon {
  width: 64px;
  height: 64px;
  border-radius: var(--radius-xl);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all var(--transition-base);
  position: relative;
  z-index: 1;
}

.stat-icon::before {
  content: '';
  position: absolute;
  inset: -2px;
  border-radius: inherit;
  padding: 2px;
  background: linear-gradient(135deg, currentColor 0%, transparent 100%);
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask-composite: exclude;
  opacity: 0.3;
}

.stat-row .stat-card:hover .stat-icon {
  transform: scale(1.05) rotate(-5deg);
}

.stat-icon--primary {
  background: linear-gradient(135deg, var(--el-color-primary-light-9) 0%, var(--el-color-primary-light-8) 100%);
  color: var(--el-color-primary);
}

.stat-icon--success {
  background: linear-gradient(135deg, var(--el-color-success-light-9) 0%, var(--el-color-success-light-8) 100%);
  color: var(--el-color-success);
}

.stat-icon--warning {
  background: linear-gradient(135deg, var(--el-color-warning-light-9) 0%, var(--el-color-warning-light-8) 100%);
  color: var(--el-color-warning);
}

.stat-icon--danger {
  background: linear-gradient(135deg, var(--el-color-danger-light-9) 0%, var(--el-color-danger-light-8) 100%);
  color: var(--el-color-danger);
}

.stat-info {
  flex: 1;
  position: relative;
  z-index: 1;
}

.stat-value {
  font-size: var(--font-size-3xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
  line-height: 1.2;
  letter-spacing: -0.5px;
  margin-bottom: 4px;
}

.stat-label {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  font-weight: var(--font-weight-medium);
}
</style>