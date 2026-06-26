<template>
  <OrderListView
    title="采购记录"
    order-type="purchase"
    :api="api"
    add-label="新建采购"
    confirm-text="确认采购(自动入库)"
    empty-label="采购记录"
    title-name="采购"
    partner-label="供应商"
    partner-mode="select"
    partner-field="supplier_id"
    payment-status-label="付款状态"
    delete-confirm-text="确定删除此采购单？删除后将扣减对应库存"
    show-keyword-search
    :default-form="PURCHASE_DEFAULTS"
    :auto-fill-price="true"
  />
</template>

<script setup>
import ordersApi from '../api/orders'
import OrderListView from '../components/OrderListView.vue'

const api = { create: ordersApi.createPurchase, update: ordersApi.updatePurchase, delete: ordersApi.deletePurchase, getList: ordersApi.getPurchases }
const PURCHASE_DEFAULTS = { supplier_id: null, tax_rate: 0.03, has_invoice: false, payment_method: 'company', payment_status: 'unpaid', notes: '', image_url: '' }
</script>
