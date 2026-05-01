<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="font-weight:600;">报表统计</span>
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
          <el-row :gutter="16" style="margin-bottom:16px;">
            <el-col :span="6">
              <div class="stat-card">
                <div class="stat-value">{{ overview.total_products || 0 }}</div>
                <div class="stat-label">商品种类</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-card">
                <div class="stat-value">{{ overview.total_inventory_quantity || 0 }}</div>
                <div class="stat-label">库存总量</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-card">
                <div class="stat-value">¥{{ (overview.total_stock_value || 0).toLocaleString() }}</div>
                <div class="stat-label">库存价值</div>
              </div>
            </el-col>
            <el-col :span="6">
              <div class="stat-card">
                <div class="stat-value">{{ overview.low_stock_count || 0 }}</div>
                <div class="stat-label">库存预警</div>
              </div>
            </el-col>
          </el-row>
        </el-tab-pane>

        <el-tab-pane label="采购报表" name="purchase">
          <div style="margin-bottom:12px;display:flex;gap:12px;">
            <el-date-picker v-model="purchaseDateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" @change="loadPurchaseReport" />
          </div>
          <div style="margin-bottom:12px;font-size:16px;font-weight:600;">
            采购总金额：¥{{ purchaseReport.total_amount?.toLocaleString() || '0.00' }} | 采购单数：{{ purchaseReport.count || 0 }}
          </div>
          <el-table :data="purchaseReport.items || []" stripe size="small" style="width:100%" @expand-change="()=>{}">
            <el-table-column type="expand" width="40">
              <template #default="{ row }">
                <div style="padding:8px 24px;">
                  <el-table :data="row.items" size="small" :border="true" style="width:100%">
                    <el-table-column prop="product_name" label="商品" min-width="120" />
                    <el-table-column prop="quantity" label="数量" width="80" />
                    <el-table-column prop="unit_price" label="单价" width="90"><template #default="{ row: item }">¥{{ item.unit_price?.toFixed(2) }}</template></el-table-column>
                    <el-table-column prop="total_price" label="小计" width="100"><template #default="{ row: item }">¥{{ item.total_price?.toFixed(2) }}</template></el-table-column>
                  </el-table>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="order_no" label="单号" width="150" />
            <el-table-column prop="supplier_name" label="供应商" width="120" />
            <el-table-column prop="total_price" label="总价" width="100"><template #default="{ row }">¥{{ row.total_price?.toFixed(2) }}</template></el-table-column>
            <el-table-column prop="purchase_date" label="日期" width="110"><template #default="{ row }">{{ row.purchase_date?.slice(0, 10) }}</template></el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="销售报表" name="sale">
          <div style="margin-bottom:12px;display:flex;gap:12px;">
            <el-date-picker v-model="saleDateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" @change="loadSaleReport" />
          </div>
          <div style="margin-bottom:12px;font-size:16px;font-weight:600;">
            销售总金额：¥{{ saleReport.total_amount?.toLocaleString() || '0.00' }} | 销售单数：{{ saleReport.count || 0 }}
          </div>
          <el-table :data="saleReport.items || []" stripe size="small" style="width:100%">
            <el-table-column type="expand" width="40">
              <template #default="{ row }">
                <div style="padding:8px 24px;">
                  <el-table :data="row.items" size="small" :border="true" style="width:100%">
                    <el-table-column prop="product_name" label="商品" min-width="120" />
                    <el-table-column prop="quantity" label="数量" width="80" />
                    <el-table-column prop="unit_price" label="单价" width="90"><template #default="{ row: item }">¥{{ item.unit_price?.toFixed(2) }}</template></el-table-column>
                    <el-table-column prop="total_price" label="小计" width="100"><template #default="{ row: item }">¥{{ item.total_price?.toFixed(2) }}</template></el-table-column>
                  </el-table>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="order_no" label="单号" width="150" />
            <el-table-column prop="customer_name" label="客户" width="120" />
            <el-table-column prop="total_price" label="总价" width="100"><template #default="{ row }">¥{{ row.total_price?.toFixed(2) }}</template></el-table-column>
            <el-table-column prop="sale_date" label="日期" width="110"><template #default="{ row }">{{ row.sale_date?.slice(0, 10) }}</template></el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="利润分析" name="profit">
          <div style="margin-bottom:12px;display:flex;gap:12px;">
            <el-date-picker v-model="profitDateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" @change="loadProfitReport" />
          </div>
          <el-row :gutter="16">
            <el-col :span="8">
              <div class="stat-card">
                <div class="stat-value" style="color:var(--warning);">¥{{ profitReport.total_purchase_amount?.toLocaleString() || '0.00' }}</div>
                <div class="stat-label">采购总金额 ({{ profitReport.purchase_count || 0 }}单)</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-card">
                <div class="stat-value" style="color:var(--primary);">¥{{ profitReport.total_sale_amount?.toLocaleString() || '0.00' }}</div>
                <div class="stat-label">销售总金额 ({{ profitReport.sale_count || 0 }}单)</div>
              </div>
            </el-col>
            <el-col :span="8">
              <div class="stat-card">
                <div class="stat-value" :style="{ color: (profitReport.total_profit || 0) >= 0 ? 'var(--success)' : 'var(--danger)' }">¥{{ profitReport.total_profit?.toLocaleString() || '0.00' }}</div>
                <div class="stat-label">利润</div>
              </div>
            </el-col>
          </el-row>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const activeTab = ref('overview')
const overview = ref({})
const purchaseReport = ref({})
const saleReport = ref({})
const profitReport = ref({})
const purchaseDateRange = ref(null)
const saleDateRange = ref(null)
const profitDateRange = ref(null)

const loadOverview = async () => {
  try { overview.value = await api.getOverview() } catch (e) { /* ignore */ }
}

const loadPurchaseReport = async () => {
  try {
    const params = {}
    if (purchaseDateRange.value) { params.start_date = purchaseDateRange.value[0]; params.end_date = purchaseDateRange.value[1] }
    purchaseReport.value = await api.getPurchaseReport(params)
  } catch (e) { /* ignore */ }
}

const loadSaleReport = async () => {
  try {
    const params = {}
    if (saleDateRange.value) { params.start_date = saleDateRange.value[0]; params.end_date = saleDateRange.value[1] }
    saleReport.value = await api.getSaleReport(params)
  } catch (e) { /* ignore */ }
}

const loadProfitReport = async () => {
  try {
    const params = {}
    if (profitDateRange.value) { params.start_date = profitDateRange.value[0]; params.end_date = profitDateRange.value[1] }
    profitReport.value = await api.getProfitReport(params)
  } catch (e) { /* ignore */ }
}

const exportReport = async (format) => {
  try {
    const typeMap = { overview: 'profit', purchase: 'purchases', sale: 'sales', profit: 'profit' }
    const dateMap = { purchase: purchaseDateRange, sale: saleDateRange, profit: profitDateRange }
    const params = {}
    const dr = dateMap[activeTab.value]
    if (dr && dr.value) { params.start_date = dr.value[0]; params.end_date = dr.value[1] }
    await api.exportFile(typeMap[activeTab.value] || 'profit', format, params)
  } catch (e) { ElMessage.error('导出失败') }
}

onMounted(() => {
  loadOverview()
  loadPurchaseReport()
  loadSaleReport()
  loadProfitReport()
})
</script>