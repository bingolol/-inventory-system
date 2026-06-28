<template>
  <div>
    <div class="card-header" style="padding: 0 0 16px 0;">
      <span class="page-title">供应链管理</span>
    </div>
    <el-tabs v-model="activeTab">
        <el-tab-pane label="采购" name="purchases" lazy>
          <OrderListView
            title="采购记录"
            order-type="purchase"
            :api="purchaseApi"
            add-label="新建采购"
            confirm-text="确认采购"
            empty-label="采购记录"
            title-name="采购"
            partner-label="供应商"
            partner-mode="select"
            partner-field="supplier_id"
            partner-prop-name="supplier_name"
            date-prop-name="purchase_date"
            :default-form="PURCHASE_DEFAULTS"
          />
        </el-tab-pane>
        <el-tab-pane label="库存" name="inventory" lazy>
          <InventorySection />
        </el-tab-pane>
        <el-tab-pane label="供应商" name="suppliers" lazy>
          <PartnerList
            title="供应商管理"
            search-placeholder="搜索供应商名称"
            name-label="供应商名称"
            add-label="新增供应商"
            add-title="新增供应商"
            edit-title="编辑供应商"
            :api="suppliersApi"
          />
        </el-tab-pane>
        <el-tab-pane label="商品" name="products" lazy>
          <ProductsPage />
        </el-tab-pane>
      </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ordersApi from '../api/orders'
import OrderListView from '../components/OrderListView.vue'
import InventorySection from '../components/InventorySection.vue'
import PartnerList from '../components/PartnerList.vue'
import ProductsPage from './Products.vue'
import partnersApi from '../api/partners'

const activeTab = ref('purchases')
const purchaseApi = { create: ordersApi.createPurchase, update: ordersApi.updatePurchase, delete: ordersApi.deletePurchase, getList: ordersApi.getPurchases }
const PURCHASE_DEFAULTS = { supplier_id: null, tax_rate: 0.03, has_invoice: false, payment_method: 'company', payment_status: 'unpaid', notes: '', total_price: null, purchase_date: new Date().toISOString().slice(0, 10) }

const suppliersApi = {
  getList: partnersApi.getSuppliers,
  create: partnersApi.createSupplier,
  update: partnersApi.updateSupplier,
  delete: partnersApi.deleteSupplier,
}
</script>
