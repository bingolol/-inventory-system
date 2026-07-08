<template>
  <div>
    <div class="card-header" style="padding: 0 0 16px 0;">
      <span class="page-title">销售管理</span>
    </div>
    <el-tabs v-model="activeTab">
        <el-tab-pane label="销售" name="sales" lazy>
          <OrderListView
            title="销售记录"
            order-type="sale"
            :api="saleApi"
            add-label="新建销售"
            confirm-text="确认销售"
            empty-label="销售记录"
            title-name="销售"
            partner-label="客户"
            partner-mode="createable"
            partner-field="customer_name"
            partner-prop-name="customer_name"
            date-prop-name="sale_date"
            delete-confirm-text="确定删除此销售单？"
            :default-form="SALE_DEFAULTS"
          />
        </el-tab-pane>
        <el-tab-pane label="客户" name="customers">
          <PartnerList
            title="客户管理"
            search-placeholder="搜索客户名称"
            name-label="客户名称"
            add-label="新增客户"
            add-title="新增客户"
            edit-title="编辑客户"
            :api="customersApi"
          />
        </el-tab-pane>
      </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import OrderListView from '../components/OrderListView.vue'
import PartnerList from '../components/PartnerList.vue'
import ordersApi from '../api/orders'
import partnersApi from '../api/partners'
import { today } from '../utils/date'

const activeTab = ref('sales')

const saleApi = { create: ordersApi.createSale, update: ordersApi.updateSale, delete: ordersApi.deleteSale, getList: ordersApi.getSales }
const SALE_DEFAULTS = { customer_name: '', tax_rate: 0.03, has_invoice: false, payment_status: 'unpaid', notes: '', image_url: '', total_price: null, sale_date: today() }

const customersApi = {
  getList: partnersApi.getCustomers,
  create: partnersApi.createCustomer,
  update: partnersApi.updateCustomer,
  delete: partnersApi.deleteCustomer,
}
</script>
