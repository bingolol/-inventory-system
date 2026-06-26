<template>
  <OrderListView
    title="销售记录"
    order-type="sale"
    :api="api"
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
</template>

<script setup>
import ordersApi from '../api/orders'
import OrderListView from '../components/OrderListView.vue'

const api = { create: ordersApi.createSale, update: ordersApi.updateSale, delete: ordersApi.deleteSale, getList: ordersApi.getSales }
const SALE_DEFAULTS = { customer_name: '', tax_rate: 0.03, has_invoice: false, payment_status: 'unpaid', notes: '', image_url: '', total_price: null, sale_date: new Date().toISOString().slice(0, 10) }
</script>
