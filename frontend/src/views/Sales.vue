<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">销售记录</span>
          <div class="card-header-actions">
            <el-button type="primary" @click="showCreate()"><el-icon><Plus /></el-icon> 新建销售</el-button>
            <el-dropdown>
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
        <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" @change="loadData" />
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width:120px" @change="loadData">
          <el-option v-for="opt in enumsStore.orderStatusOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
      </div>
      <el-table :data="list" stripe style="width:100%" v-loading="loading">
        <template #empty>
          <el-empty description="暂无销售记录" />
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
        <el-table-column prop="customer_name" label="客户" width="120" />
        <el-table-column label="商品数" width="80"><template #default="{ row }">{{ row.items?.length || 0 }}</template></el-table-column>
        <el-table-column prop="total_price" label="总价" width="110" align="right"><template #default="{ row }"><span class="money">¥{{ formatMoney(row.total_price) }}</span></template></el-table-column>
        <el-table-column prop="has_invoice" label="已开票" width="80" align="center"><template #default="{ row }"><el-tag :type="row.has_invoice?'success':'info'" size="small">{{ row.has_invoice?'是':'否' }}</el-tag></template></el-table-column>
        <el-table-column prop="payment_status" label="支付状态" width="100" align="center"><template #default="{ row }"><StatusTag :status="row.payment_status" type="payment_status" size="small" /></template></el-table-column>
        <el-table-column prop="status" label="状态" width="90"><template #default="{ row }"><StatusTag :status="row.status" type="order" size="small" /></template></el-table-column>
        <el-table-column prop="sale_date" label="日期" width="110"><template #default="{ row }">{{ formatDate(row.sale_date) }}</template></el-table-column>
        <el-table-column prop="notes" label="备注" min-width="100" />
        <el-table-column label="附件" width="70" align="center"><template #default="{ row }"><el-image v-if="row.image_url" :src="resolveImageUrl(row.image_url)" style="width:36px;height:36px;border-radius:4px" fit="cover" :preview-src-list="[resolveImageUrl(row.image_url)]" preview-teleported /><span v-else style="color:#999;font-size:12px">无</span></template></el-table-column>
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
            <el-popconfirm title="确定删除此销售单？" @confirm="orderForm.handleDelete(row.id)"><template #reference><el-button size="small" link type="danger" style="margin-left:4px">删除</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination v-model:current-page="pagination.page.value" v-model:page-size="pagination.pageSize.value" :total="pagination.total.value" :page-sizes="[10,20,50,100]" layout="total, sizes, prev, pager, next" @current-change="loadData" @size-change="pagination.onSizeChange" />
      </div>
    </el-card>

    <SaleFormDialog 
      v-model:visible="orderForm.dialogVisible.value" 
      :is-edit="false" 
      :form="orderForm.form.value" 
      :products="orderForm.products.value" 
      :customers="customers" 
      :order-total="orderForm.orderTotal.value" 
      :on-product-change="orderForm.onItemProductChange" 
      :operation-feedback="orderForm.operationFeedback.value"
      @save="handleSave" 
      @clear-feedback="orderForm.clearFeedback" 
    />
    <SaleFormDialog 
      v-model:visible="orderForm.editDialogVisible.value" 
      :is-edit="true" 
      :form="orderForm.editForm.value" 
      :products="orderForm.products.value" 
      :customers="customers" 
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
import commonApi, { formatMoney } from '../api/common'
import { formatDate, splitOrderNo } from '../utils/format'
import { resolveImageUrl } from '../api/index'
import StatusTag from '../components/StatusTag.vue'
import SaleFormDialog from '../components/SaleFormDialog.vue'
import { useEnumsStore } from '../stores/enums'
import { useOrderForm } from '../composables/useOrderForm'
import { useOrderList } from '../composables/useOrderList'
import { useAccountAwareData } from '../composables/useAccountAwareData'

const enumsStore = useEnumsStore()
const customers = ref([])

// 使用订单列表 composable
const orderList = useOrderList({
  api: { getList: ordersApi.getSales },
  exportType: 'sales'
})

const { list, loading, dateRange, statusFilter, pagination, loadData, exportData } = orderList

const orderForm = useOrderForm({
  orderType: 'sale',
  api: { create: ordersApi.createSale, update: ordersApi.updateSale, delete: ordersApi.deleteSale },
  onSuccess: loadData,
  autoFillPrice: false
})

const SALE_DEFAULTS = { customer_name: '', tax_rate: 0.03, has_invoice: false, payment_status: 'unpaid', notes: '', image_url: '', total_price: null, sale_date: new Date().toISOString().slice(0, 10) }

async function loadOptions() {
  try {
    const [pRes, cRes] = await Promise.all([
      productsApi.getProducts({ page: 1, page_size: 1000 }),
      partnersApi.getCustomers({ page: 1, page_size: 1000 })
    ])
    orderForm.products.value = pRes.items || pRes
    customers.value = cRes.items || cRes
  } catch (e) { console.error('加载选项数据失败:', e) }
}

function showCreate() {
  orderForm.resetForm({ ...SALE_DEFAULTS })
  orderForm.dialogVisible.value = true
  loadOptions()
}

function showEdit(row) {
  orderForm.setEditForm(row, { customer_name: row.customer_name || '', has_invoice: row.has_invoice, payment_status: row.payment_status, notes: row.notes || '', image_url: row.image_url || '', total_price: Number(row.total_price) || null })
  orderForm.editDialogVisible.value = true
  loadOptions()
}

async function resolveCustomerId(name) {
  if (!name?.trim()) return null
  const existing = customers.value.find(c => c.name === name.trim())
  if (existing) return existing.id
  const created = await partnersApi.createCustomer({ name: name.trim() })
  customers.value.push(created)
  return created.id
}

async function handleSave() {
  const validItems = orderForm.form.value.items.filter(i => i.product_id && i.quantity > 0)
  if (validItems.length === 0) { ElMessage.warning('请至少添加一个有效商品'); return }
  try {
    const f = orderForm.form.value
    await ordersApi.createSale({
      customer_id: await resolveCustomerId(f.customer_name),
      has_invoice: f.has_invoice, payment_status: f.payment_status, notes: f.notes,
      total_price: f.total_price ?? undefined,
      sale_date: f.sale_date,
      items: validItems.map(i => ({ product_id: i.product_id, quantity: i.quantity, unit_price: i.unit_price }))
    })
    
    // 构建联动反馈
    const feedback = {
      show: true,
      type: 'success',
      message: '销售成功',
      details: [
        { label: '库存扣减', value: '零售出库' },
        { label: '销售商品数', value: `${validItems.length} 种` }
      ]
    }
    
    orderForm.operationFeedback.value = feedback
    orderForm.dialogVisible.value = false
    loadData()
  } catch (e) { 
    ElMessage.error('销售失败: ' + (e.response?.data?.detail || e.message)) 
  }
}

async function handleEditSave() {
  const validItems = orderForm.editForm.value.items.filter(i => i.product_id && i.quantity > 0)
  try {
    const f = orderForm.editForm.value
    await ordersApi.updateSale(f.id, {
      customer_id: await resolveCustomerId(f.customer_name),
      has_invoice: f.has_invoice, payment_status: f.payment_status, notes: f.notes,
      image_url: f.image_url, total_price: f.total_price ?? undefined,
      items: validItems.map(i => ({ product_id: i.product_id, quantity: i.quantity, unit_price: i.unit_price }))
    })
    ElMessage.success(validItems.length === 0 ? '销售单已删除（商品行数归零）' : '销售单修改成功')
    orderForm.editDialogVisible.value = false; loadData()
  } catch (e) { ElMessage.error('修改失败: ' + (e.response?.data?.detail || e.message)) }
}

useAccountAwareData(loadData)
enumsStore.fetchEnums()
</script>