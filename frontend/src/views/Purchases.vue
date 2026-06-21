<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">采购记录</span>
          <div>
            <el-button type="primary" @click="showCreate()"><el-icon><Plus /></el-icon> 新建采购</el-button>
            <el-dropdown style="margin-left:8px">
              <el-button><el-icon><Download /></el-icon> 导出</el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item @click="exportData('excel')">Excel</el-dropdown-item>
                  <el-dropdown-item @click="exportData('csv')">CSV</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </template>
      <div class="filter-bar">
        <el-input v-model="keyword" placeholder="搜索单号/供应商/项目" clearable style="width:220px" @clear="loadData" @keyup.enter="loadData">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" @change="loadData" />
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width:120px" @change="loadData">
          <el-option v-for="opt in enumsStore.orderStatusOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
        <el-button type="primary" @click="loadData"><el-icon><Search /></el-icon> 查询</el-button>
      </div>
      <el-table :data="list" stripe style="width:100%" v-loading="loading" show-summary :summary-method="getSummaries">
        <template #empty>
          <el-empty description="暂无采购记录" />
        </template>
        <el-table-column type="expand" width="40">
          <template #default="{ row }">
            <div style="padding:8px 24px">
              <el-table :data="row.items" size="small" :border="true" style="width:100%">
                <el-table-column prop="product_name" label="商品" min-width="120" />
                <el-table-column prop="quantity" label="数量" width="80" />
                <el-table-column prop="unit_price" label="单价" width="100" align="right"><template #default="{ row: item }"><span class="money">¥{{ formatMoney(item.unit_price) }}</span></template></el-table-column>
                <el-table-column prop="total_price" label="小计" width="110" align="right"><template #default="{ row: item }"><span class="money">¥{{ formatMoney(item.total_price) }}</span></template></el-table-column>
              </el-table>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="order_no" label="单号" width="130">
          <template #default="{ row }">
            <div class="order-no">
              <div class="order-no-line1">{{ splitOrderNo(row.order_no).line1 }}</div>
              <div class="order-no-line2">{{ splitOrderNo(row.order_no).line2 }}</div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="supplier_name" label="供应商" width="120" />
        <el-table-column label="商品数" width="80"><template #default="{ row }">{{ row.items?.length || 0 }}</template></el-table-column>
        <el-table-column prop="total_price" label="总价" width="110" align="right"><template #default="{ row }"><span class="money">¥{{ formatMoney(row.total_price) }}</span></template></el-table-column>
        <el-table-column prop="has_invoice" label="已开票" width="80" align="center"><template #default="{ row }"><el-tag :type="row.has_invoice?'success':'info'" size="small">{{ row.has_invoice?'是':'否' }}</el-tag></template></el-table-column>
        <el-table-column prop="payment_method" label="支付方式" width="100" align="center"><template #default="{ row }"><el-tag :type="row.payment_method==='company'?'primary':'warning'" size="small">{{ enumsStore.getLabel('payment_method', row.payment_method) }}</el-tag></template></el-table-column>
        <el-table-column prop="payment_status" label="付款状态" width="90" align="center"><template #default="{ row }"><StatusTag :status="row.payment_status" type="payment_status" size="small" /></template></el-table-column>
        <el-table-column prop="status" label="状态" width="90"><template #default="{ row }"><StatusTag :status="row.status" type="order" size="small" /></template></el-table-column>
        <el-table-column prop="purchase_date" label="日期" width="110"><template #default="{ row }">{{ formatDate(row.purchase_date) }}</template></el-table-column>
        <el-table-column prop="notes" label="备注" min-width="100" />
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" link type="primary" @click="showEdit(row)">编辑</el-button>
            <el-dropdown v-if="row.status==='pending'" style="margin-left:4px">
              <el-button size="small" link type="primary">状态<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown><el-dropdown-menu><el-dropdown-item @click="orderForm.changeStatus(row.id,'completed')">完成</el-dropdown-item><el-dropdown-item @click="orderForm.changeStatus(row.id,'cancelled')">取消</el-dropdown-item></el-dropdown-menu></template>
            </el-dropdown>
            <el-dropdown v-else-if="row.status==='completed'" style="margin-left:4px">
              <el-button size="small" link type="primary">状态<el-icon class="el-icon--right"><ArrowDown /></el-icon></el-button>
              <template #dropdown><el-dropdown-menu><el-dropdown-item @click="orderForm.changeStatus(row.id,'cancelled')">取消(退回库存)</el-dropdown-item></el-dropdown-menu></template>
            </el-dropdown>
            <el-popconfirm title="确定删除此采购单？删除后将扣减对应库存" @confirm="orderForm.handleDelete(row.id)"><template #reference><el-button size="small" link type="danger" style="margin-left:4px">删除</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination v-model:current-page="pagination.page.value" v-model:page-size="pagination.pageSize.value" :total="pagination.total.value" :page-sizes="[10,20,50,100]" layout="total, sizes, prev, pager, next" @current-change="loadData" @size-change="pagination.onSizeChange" />
      </div>
    </el-card>

    <PurchaseFormDialog 
      v-model:visible="orderForm.dialogVisible.value" 
      :is-edit="false" 
      :form="orderForm.form.value" 
      :products="orderForm.products.value" 
      :suppliers="suppliers" 
      :order-total="orderForm.orderTotal.value" 
      :on-product-change="orderForm.onItemProductChange" 
      :operation-feedback="orderForm.operationFeedback.value"
      @save="handleSave" 
      @clear-feedback="orderForm.clearFeedback" 
    />
    <PurchaseFormDialog 
      v-model:visible="orderForm.editDialogVisible.value" 
      :is-edit="true" 
      :form="orderForm.editForm.value" 
      :products="orderForm.products.value" 
      :suppliers="suppliers" 
      :order-total="orderForm.editOrderTotal.value" 
      :on-product-change="orderForm.onEditItemProductChange" 
      @save="handleEditSave" 
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import ordersApi from '../api/orders'
import partnersApi from '../api/partners'
import productsApi from '../api/products'
import { formatMoney, formatDate, splitOrderNo } from '../utils/format'
import { handleError } from '../api/index'
import StatusTag from '../components/StatusTag.vue'
import PurchaseFormDialog from '../components/PurchaseFormDialog.vue'
import { useEnumsStore } from '../stores/enums'
import { useOrderForm } from '../composables/useOrderForm'
import { useOrderList } from '../composables/useOrderList'
import { useAccountAwareData } from '../composables/useAccountAwareData'

const enumsStore = useEnumsStore()
const suppliers = ref([])

// 使用订单列表 composable
const orderList = useOrderList({
  api: { getList: ordersApi.getPurchases },
  exportType: 'purchases'
})

const { list, loading, keyword, dateRange, statusFilter, pagination, loadData, exportData, getSummaries } = orderList

const orderForm = useOrderForm({
  orderType: 'purchase',
  api: { create: ordersApi.createPurchase, update: ordersApi.updatePurchase, delete: ordersApi.deletePurchase },
  onSuccess: loadData,
  autoFillPrice: true
})

const PURCHASE_DEFAULTS = { supplier_id: null, tax_rate: 0.03, has_invoice: false, payment_method: 'company', payment_status: 'unpaid', notes: '', image_url: '' }

async function loadOptions() {
  try {
    const [pRes, sRes] = await Promise.all([
      productsApi.getProducts({ page: 1, page_size: 1000 }),
      partnersApi.getSuppliers({ page: 1, page_size: 1000 })
    ])
    orderForm.products.value = pRes.items || pRes
    suppliers.value = sRes.items || sRes
  } catch (e) { /* ignore */ }
}

function showCreate() {
  orderForm.resetForm({ ...PURCHASE_DEFAULTS })
  orderForm.dialogVisible.value = true
  loadOptions()
}

function showEdit(row) {
  orderForm.setEditForm(row, { supplier_id: row.supplier_id, tax_rate: Number(row.tax_rate) || 0.13, has_invoice: row.has_invoice, payment_method: row.payment_method, payment_status: row.payment_status || 'unpaid', notes: row.notes || '', image_url: row.image_url || '' })
  orderForm.editDialogVisible.value = true
  loadOptions()
}

async function handleSave() {
  const validItems = orderForm.form.value.items.filter(i => i.product_id && i.quantity > 0)
  if (validItems.length === 0) { ElMessage.warning('请至少添加一个有效商品'); return }
  try {
    const f = orderForm.form.value
    await ordersApi.createPurchase({
      supplier_id: f.supplier_id, tax_rate: f.tax_rate,
      has_invoice: f.has_invoice, payment_method: f.payment_method, payment_status: f.payment_status,
      notes: f.notes, items: validItems.map(i => ({ product_id: i.product_id, quantity: i.quantity, unit_price: i.unit_price }))
    })
    
    // 构建联动反馈
    const feedback = {
      show: true,
      type: 'success',
      message: '采购成功，已自动入库',
      details: [
        { label: '入库商品数', value: `${validItems.length} 种` },
        { label: '总数量', value: `${validItems.reduce((sum, i) => sum + i.quantity, 0)} 件` }
      ]
    }
    
    orderForm.operationFeedback.value = feedback
    orderForm.dialogVisible.value = false
    loadData()
  } catch (e) { handleError(e, { defaultMsg: '采购失败' }) } 
}

async function handleEditSave() {
  const validItems = orderForm.editForm.value.items.filter(i => i.product_id && i.quantity > 0)
  try {
    const f = orderForm.editForm.value
    await ordersApi.updatePurchase(f.id, {
      supplier_id: f.supplier_id, tax_rate: f.tax_rate,
      has_invoice: f.has_invoice, payment_method: f.payment_method, payment_status: f.payment_status,
      notes: f.notes, image_url: f.image_url, items: validItems.map(i => ({ product_id: i.product_id, quantity: i.quantity, unit_price: i.unit_price }))
    })
    ElMessage.success(validItems.length === 0 ? '采购单已删除（商品行数归零）' : '采购单修改成功，库存已自动调整')
    orderForm.editDialogVisible.value = false; loadData()
  } catch (e) { handleError(e, { defaultMsg: '修改失败' }) }
}

useAccountAwareData(loadData)
enumsStore.fetchEnums()
</script>