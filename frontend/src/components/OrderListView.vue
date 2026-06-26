<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">{{ title }}</span>
          <div>
            <el-button type="primary" @click="showCreate"><el-icon><Plus /></el-icon> {{ addLabel }}</el-button>
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
        <el-input v-if="showKeywordSearch" v-model="keyword" placeholder="搜索单号/供应商/项目" clearable style="width:220px" @clear="loadData" @keyup.enter="loadData">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-date-picker v-model="dateRange" type="daterange" range-separator="至" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" @change="loadData" />
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width:120px" @change="loadData">
          <el-option v-for="opt in enumsStore.orderStatusOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
        <el-button v-if="showKeywordSearch" type="primary" @click="loadData"><el-icon><Search /></el-icon> 查询</el-button>
      </div>
      <el-table :data="list" stripe style="width:100%" v-loading="loading" show-summary :summary-method="getSummaries">
        <template #empty>
          <el-empty :description="'暂无' + emptyLabel" />
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
        <el-table-column :prop="partnerPropName" :label="partnerLabel" width="120" />
        <el-table-column label="商品数" width="80"><template #default="{ row }">{{ row.items?.length || 0 }}</template></el-table-column>
        <el-table-column prop="total_price" label="总价" width="110" align="right"><template #default="{ row }"><span class="money">¥{{ formatMoney(row.total_price) }}</span></template></el-table-column>
        <el-table-column prop="has_invoice" label="已开票" width="80" align="center"><template #default="{ row }"><el-tag :type="row.has_invoice?'success':'info'" size="small">{{ row.has_invoice?'是':'否' }}</el-tag></template></el-table-column>
        <el-table-column v-if="orderType==='purchase'" prop="payment_method" label="支付方式" width="100" align="center"><template #default="{ row }"><el-tag :type="row.payment_method==='company'?'primary':'warning'" size="small">{{ enumsStore.getLabel('payment_method', row.payment_method) }}</el-tag></template></el-table-column>
        <el-table-column prop="payment_status" :label="paymentStatusLabel" width="100" align="center"><template #default="{ row }"><StatusTag :status="row.payment_status" type="payment_status" size="small" /></template></el-table-column>
        <el-table-column prop="status" label="状态" width="90"><template #default="{ row }"><StatusTag :status="row.status" type="order" size="small" /></template></el-table-column>
        <el-table-column :prop="datePropName" label="日期" width="110"><template #default="{ row }">{{ formatDate(row[datePropName]) }}</template></el-table-column>
        <el-table-column prop="notes" label="备注" min-width="100" />
        <el-table-column v-if="orderType==='sale'" label="附件" width="70" align="center">
          <template #default="{ row }">
            <el-image v-if="row.image_url" :src="resolveImageUrl(row.image_url)" style="width:36px;height:36px;border-radius:4px" fit="cover" :preview-src-list="[resolveImageUrl(row.image_url)]" preview-teleported />
            <span v-else style="color:#999;font-size:12px">无</span>
          </template>
        </el-table-column>
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
            <el-popconfirm :title="deleteConfirmText" @confirm="orderForm.handleDelete(row.id)"><template #reference><el-button size="small" link type="danger" style="margin-left:4px">删除</el-button></template></el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination-bar">
        <el-pagination v-model:current-page="pagination.page.value" v-model:page-size="pagination.pageSize.value" :total="pagination.total.value" :page-sizes="[10,20,50,100]" layout="total, sizes, prev, pager, next" @current-change="loadData" @size-change="pagination.onSizeChange" />
      </div>
    </el-card>

    <OrderFormDialog 
      v-model:visible="orderForm.dialogVisible.value" 
      :is-edit="false" 
      :form="orderForm.form.value" 
      :products="products" 
      :partners="partners" 
      :order-total="orderForm.orderTotal.value" 
      :on-product-change="orderForm.onItemProductChange" 
      :operation-feedback="orderForm.operationFeedback.value"
      :title-name="titleName"
      :partner-label="partnerLabel"
      :partner-field="partnerField"
      :partner-mode="partnerMode"
      :show-date="orderType==='sale'"
      :show-tax-rate-on-edit="orderType!=='sale'"
      :show-stock="orderType==='sale'"
      :show-custom-price="orderType==='sale'"
      :show-payment-method="orderType==='purchase'"
      :use-enums-for-payment="orderType==='purchase'"
      :business-type="orderType"
      :confirm-text="confirmText"
      :update-api="(id, data) => api.update(id, data)"
      @save="handleSave" 
      @clear-feedback="orderForm.clearFeedback" 
    />
    <OrderFormDialog 
      v-model:visible="orderForm.editDialogVisible.value" 
      :is-edit="true" 
      :form="orderForm.editForm.value" 
      :products="products" 
      :partners="partners" 
      :order-total="orderForm.editOrderTotal.value" 
      :on-product-change="orderForm.onEditItemProductChange"
      :title-name="titleName"
      :partner-label="partnerLabel"
      :partner-field="partnerField"
      :partner-mode="partnerMode"
      :show-date="false"
      :show-tax-rate-on-edit="orderType!=='sale'"
      :show-stock="orderType==='sale'"
      :show-custom-price="orderType==='sale'"
      :show-payment-method="orderType==='purchase'"
      :use-enums-for-payment="orderType==='purchase'"
      :business-type="orderType"
      :update-api="(id, data) => api.update(id, data)"
      @save="handleEditSave" 
    />
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import partnersApi from '../api/partners'
import { formatMoney, formatDate, splitOrderNo } from '../utils/format'
import { resolveImageUrl, handleError } from '../api/index'
import StatusTag from './StatusTag.vue'
import OrderFormDialog from './OrderFormDialog.vue'
import { useOrderPage } from '../composables/useOrderPage'

const props = defineProps({
  title: { type: String, required: true },
  orderType: { type: String, required: true },
  api: { type: Object, required: true },
  addLabel: { type: String, default: '新建' },
  confirmText: { type: String, default: '确认' },
  emptyLabel: { type: String, default: '记录' },
  titleName: { type: String, default: '' },
  partnerLabel: { type: String, default: '' },
  partnerMode: { type: String, default: 'select' },
  partnerField: { type: String, default: 'supplier_id' },
  partnerPropName: { type: String, default: 'supplier_name' },
  datePropName: { type: String, default: 'purchase_date' },
  paymentStatusLabel: { type: String, default: '支付状态' },
  deleteConfirmText: { type: String, default: '确定删除？' },
  showKeywordSearch: { type: Boolean, default: false },
  defaultForm: { type: Object, default: () => ({}) },
  autoFillPrice: { type: Boolean, default: false }
})

const {
  list, loading, keyword, dateRange, statusFilter, pagination,
  loadData, exportData, getSummaries,
  orderForm, enumsStore, products, partners, loadOptions
} = useOrderPage({
  orderType: props.orderType,
  api: props.api,
  exportType: props.orderType === 'sale' ? 'sales' : 'purchases',
  autoFillPrice: props.autoFillPrice
})

async function loadPartnerOptions() {
  const fn = props.orderType === 'sale'
    ? (p) => partnersApi.getCustomers(p)
    : (p) => partnersApi.getSuppliers(p)
  await loadOptions(fn)
}

function showCreate() {
  orderForm.resetForm({ ...props.defaultForm })
  orderForm.dialogVisible.value = true
  loadPartnerOptions()
}

function showEdit(row) {
  const defaults = props.orderType === 'sale'
    ? { customer_name: row.customer_name || '', has_invoice: row.has_invoice, payment_status: row.payment_status, notes: row.notes || '', image_url: row.image_url || '', total_price: Number(row.total_price) || null }
    : { supplier_id: row.supplier_id, tax_rate: Number(row.tax_rate) || 0.13, has_invoice: row.has_invoice, payment_method: row.payment_method, payment_status: row.payment_status || 'unpaid', notes: row.notes || '', image_url: row.image_url || '' }
  orderForm.setEditForm(row, defaults)
  orderForm.editDialogVisible.value = true
  loadPartnerOptions()
}

async function resolveCustomerId(name) {
  if (props.orderType !== 'sale') return null
  if (!name?.trim()) return null
  const existing = partners.value.find(c => c.name === name.trim())
  if (existing) return existing.id
  const created = await partnersApi.createCustomer({ name: name.trim() })
  partners.value.push(created)
  return created.id
}

async function handleSave() {
  const validItems = orderForm.form.value.items.filter(i => i.product_id && i.quantity > 0)
  if (validItems.length === 0) { ElMessage.warning('请至少添加一个有效商品'); return }
  try {
    const f = orderForm.form.value
    const items = validItems.map(i => ({ product_id: i.product_id, quantity: i.quantity, unit_price: i.unit_price }))
    
    if (props.orderType === 'sale') {
      await props.api.create({
        customer_id: await resolveCustomerId(f.customer_name),
        has_invoice: f.has_invoice, payment_status: f.payment_status, notes: f.notes,
        total_price: f.total_price ?? undefined,
        sale_date: f.sale_date,
        items
      })
      orderForm.operationFeedback.value = {
        show: true, type: 'success', message: '销售成功',
        details: [
          { label: '库存扣减', value: '零售出库' },
          { label: '销售商品数', value: `${validItems.length} 种` }
        ]
      }
    } else {
      await props.api.create({
        supplier_id: f.supplier_id, tax_rate: f.tax_rate,
        has_invoice: f.has_invoice, payment_method: f.payment_method, payment_status: f.payment_status,
        notes: f.notes, items
      })
      orderForm.operationFeedback.value = {
        show: true, type: 'success', message: '采购成功，已自动入库',
        details: [
          { label: '入库商品数', value: `${validItems.length} 种` },
          { label: '总数量', value: `${validItems.reduce((sum, i) => sum + i.quantity, 0)} 件` }
        ]
      }
    }
    
    orderForm.dialogVisible.value = false
    loadData()
  } catch (e) { handleError(e, { defaultMsg: props.orderType === 'sale' ? '销售失败' : '采购失败' }) }
}

async function handleEditSave() {
  const validItems = orderForm.editForm.value.items.filter(i => i.product_id && i.quantity > 0)
  try {
    const f = orderForm.editForm.value
    const items = validItems.map(i => ({ product_id: i.product_id, quantity: i.quantity, unit_price: i.unit_price }))
    const orderLabel = props.orderType === 'sale' ? '销售单' : '采购单'
    
    if (props.orderType === 'sale') {
      await props.api.update(f.id, {
        customer_id: await resolveCustomerId(f.customer_name),
        has_invoice: f.has_invoice, payment_status: f.payment_status, notes: f.notes,
        image_url: f.image_url, total_price: f.total_price ?? undefined,
        items
      })
    } else {
      await props.api.update(f.id, {
        supplier_id: f.supplier_id, tax_rate: f.tax_rate,
        has_invoice: f.has_invoice, payment_method: f.payment_method, payment_status: f.payment_status,
        notes: f.notes, image_url: f.image_url, items
      })
    }
    ElMessage.success(validItems.length === 0 ? `${orderLabel}已删除（商品行数归零）` : `${orderLabel}修改成功`)
    orderForm.editDialogVisible.value = false
    loadData()
  } catch (e) { handleError(e, { defaultMsg: '修改失败' }) }
}
</script>
