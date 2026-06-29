<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">报表统计</span>
          <el-dropdown>
            <el-button size="small"><el-icon><Download /></el-icon> 导出当前报表</el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="exportReport('excel')">Excel</el-dropdown-item>
                <el-dropdown-item @click="exportReport('csv')">CSV</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </template>
      <el-tabs v-model="activeTab">
        <el-tab-pane label="总览" name="overview">
          <div class="rp-stats">
            <div class="rp-stat"><span class="rp-stat-label">商品种类</span><span class="rp-stat-value c-primary">{{ overview.total_products ?? 0 }}</span></div>
            <div class="rp-stat"><span class="rp-stat-label">库存总量</span><span class="rp-stat-value c-success">{{ overview.total_inventory_quantity ?? 0 }} 件</span></div>
            <div class="rp-stat"><span class="rp-stat-label">库存价值</span><span class="rp-stat-value c-warning">¥{{ (overview.total_stock_value ?? 0).toLocaleString() }}</span></div>
            <div class="rp-stat"><span class="rp-stat-label">库存预警</span><span class="rp-stat-value" :style="{ color: (overview.low_stock_count ?? 0) > 0 ? 'var(--danger)' : 'var(--success)' }">{{ overview.low_stock_count ?? 0 }}</span></div>
          </div>
        </el-tab-pane>

        <el-tab-pane label="采购报表" name="purchase">
          <div class="rp-filter">
            <el-date-picker v-model="purchaseDateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" @change="loadPurchaseReport" />
          </div>
          <div class="rp-summary">采购总金额：¥{{ purchaseReport.total_amount?.toLocaleString() || '0.00' }} | 采购单数：{{ purchaseReport.count || 0 }}</div>
          <el-table :data="purchaseReport.items || []" stripe size="small" style="width:100%" @expand-change="()=>{}">
            <el-table-column type="expand" width="40">
              <template #default="{ row }">
                <div style="padding:8px 24px;">
                  <el-table :data="row.items" size="small" :border="true" style="width:100%">
                    <el-table-column prop="product_name" label="商品" min-width="120" />
                    <el-table-column prop="quantity" label="数量" width="80" />
                    <el-table-column prop="unit_price" label="单价" width="90"><template #default="{ row: item }">¥{{ formatMoney(item.unit_price) }}</template></el-table-column>
                    <el-table-column prop="total_price" label="小计" width="100"><template #default="{ row: item }">¥{{ formatMoney(item.total_price) }}</template></el-table-column>
                  </el-table>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="order_no" label="单号" min-width="130">
              <template #default="{ row }">
                <div class="order-no">
                  <div class="order-no-line1">{{ splitOrderNo(row.order_no).line1 }}</div>
                  <div class="order-no-line2">{{ splitOrderNo(row.order_no).line2 }}</div>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="supplier_name" label="供应商" min-width="120" />
            <el-table-column prop="total_price" label="总价" min-width="100"><template #default="{ row }"><span class="money">¥{{ formatMoney(row.total_price) }}</span></template></el-table-column>
            <el-table-column prop="purchase_date" label="日期" min-width="110"><template #default="{ row }">{{ formatDate(row.purchase_date) }}</template></el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="销售报表" name="sale">
          <div class="filter-bar">
            <el-date-picker v-model="saleDateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" @change="loadSaleReport" />
          </div>
          <div class="rp-summary">销售总金额：¥{{ saleReport.total_amount?.toLocaleString() || '0.00' }} | 销售单数：{{ saleReport.count || 0 }}</div>
          <el-table :data="saleReport.items || []" stripe size="small" style="width:100%">
            <el-table-column type="expand" width="40">
              <template #default="{ row }">
                <div style="padding:8px 24px;">
                  <el-table :data="row.items" size="small" :border="true" style="width:100%">
                    <el-table-column prop="product_name" label="商品" min-width="120" />
                    <el-table-column prop="quantity" label="数量" width="80" />
                    <el-table-column prop="unit_price" label="单价" width="90"><template #default="{ row: item }">¥{{ formatMoney(item.unit_price) }}</template></el-table-column>
                    <el-table-column prop="total_price" label="小计" width="100"><template #default="{ row: item }">¥{{ formatMoney(item.total_price) }}</template></el-table-column>
                  </el-table>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="order_no" label="单号" min-width="130">
              <template #default="{ row }">
                <div class="order-no">
                  <div class="order-no-line1">{{ splitOrderNo(row.order_no).line1 }}</div>
                  <div class="order-no-line2">{{ splitOrderNo(row.order_no).line2 }}</div>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="customer_name" label="客户" min-width="120" />
            <el-table-column prop="total_price" label="总价" min-width="100"><template #default="{ row }">¥{{ formatMoney(row.total_price) }}</template></el-table-column>
            <el-table-column prop="sale_date" label="日期" min-width="110"><template #default="{ row }">{{ formatDate(row.sale_date) }}</template></el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="利润分析" name="profit">
          <div class="rp-filter">
            <el-date-picker v-model="profitDateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" @change="loadProfitReport" />
          </div>
          <div class="rp-stats" style="margin-top:12px;">
            <div class="rp-stat"><span class="rp-stat-label">销售收入</span><span class="rp-stat-value c-primary">¥{{ formatMoney(profitReport.total_revenue ?? 0) }}</span><span class="rp-stat-sub">{{ profitReport.sale_count ?? 0 }} 单</span></div>
            <div class="rp-stat"><span class="rp-stat-label">商品成本</span><span class="rp-stat-value c-warning">¥{{ formatMoney(profitReport.total_cost ?? 0) }}</span></div>
            <div class="rp-stat"><span class="rp-stat-label">利润</span><span class="rp-stat-value" :style="{ color: (profitReport.total_profit ?? 0) >= 0 ? 'var(--success)' : 'var(--danger)' }">¥{{ formatMoney(profitReport.total_profit ?? 0) }}</span></div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import financeApi from '../api/finance'
import exportApi from '../api/export'
import { formatMoney, formatDate, splitOrderNo } from '../utils/format'
import { handleError } from '../api/index'
import { useAccountAwareData } from '../composables/useAccountAwareData'

const activeTab = ref('overview')
const overview = ref({})
const purchaseReport = ref({})
const saleReport = ref({})
const profitReport = ref({})
const purchaseDateRange = ref(null)
const saleDateRange = ref(null)
const _initProfitDateRange = () => {
  const now = new Date()
  const start = new Date(now.getFullYear(), now.getMonth(), 1)
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0)
  return [start.toISOString().slice(0, 10), end.toISOString().slice(0, 10)]
}
const profitDateRange = ref(_initProfitDateRange())

const loadOverview = async () => {
  try { overview.value = await financeApi.getOverview() } catch (e) { handleError(e, { defaultMsg: '加载总览数据失败，请检查账套设置是否正确' }) }
}

const loadPurchaseReport = async () => {
  try {
    const params = {}
    if (purchaseDateRange.value) { params.start_date = purchaseDateRange.value[0]; params.end_date = purchaseDateRange.value[1] }
    purchaseReport.value = await financeApi.getPurchaseReport(params)
  } catch (e) { handleError(e, { defaultMsg: '加载采购报表失败，请检查所选时间范围是否有采购数据' }) }
}

const loadSaleReport = async () => {
  try {
    const params = {}
    if (saleDateRange.value) { params.start_date = saleDateRange.value[0]; params.end_date = saleDateRange.value[1] }
    saleReport.value = await financeApi.getSaleReport(params)
  } catch (e) { handleError(e, { defaultMsg: '加载销售报表失败，请检查所选时间范围是否有销售数据' }) }
}

const loadProfitReport = async () => {
  try {
    const params = {}
    if (profitDateRange.value) { params.start_date = profitDateRange.value[0]; params.end_date = profitDateRange.value[1] }
    else {
      const now = new Date()
      params.start_date = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10)
      params.end_date = new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().slice(0, 10)
    }
    profitReport.value = await financeApi.getProfitReport(params)
  } catch (e) { handleError(e, { defaultMsg: '加载利润分析失败，请检查所选时间范围是否有已完成销售订单' }) }
}

const exportReport = async (format) => {
  try {
    const typeMap = { overview: 'profit', purchase: 'purchases', sale: 'sales', profit: 'profit' }
    const dateMap = { purchase: purchaseDateRange, sale: saleDateRange, profit: profitDateRange }
    const params = {}
    const dr = dateMap[activeTab.value]
    if (dr && dr.value) { params.start_date = dr.value[0]; params.end_date = dr.value[1] }
    await exportApi.exportFile(typeMap[activeTab.value] || 'profit', format, params)
  } catch (e) { handleError(e, { defaultMsg: '导出失败，请检查文件权限和磁盘空间' }) }
}

useAccountAwareData(loadOverview, loadPurchaseReport, loadSaleReport, loadProfitReport)
</script>

<style scoped>
.rp-stats {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}
.rp-stat {
  flex: 1;
  background: var(--bg-elevated);
  border: 1px solid var(--border-lighter);
  border-radius: 12px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.rp-stat-label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
  letter-spacing: 0.5px;
}
.rp-stat-value {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.5px;
}
.rp-stat-sub {
  font-size: 12px;
  color: var(--text-placeholder);
}
.rp-filter {
  margin-bottom: 12px;
  display: flex;
  gap: 12px;
}
.rp-summary {
  margin-bottom: 12px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-regular);
}
</style>