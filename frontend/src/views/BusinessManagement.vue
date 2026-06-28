<template>
  <div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">业务管理</span>
        </div>
      </template>

      <el-tabs v-model="activeTab">
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

        <el-tab-pane label="供应商" name="suppliers">
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

        <el-tab-pane label="采购" name="purchases">
          <OrderListView order-type="purchase" />
        </el-tab-pane>

        <el-tab-pane label="销售" name="sales">
          <OrderListView order-type="sale" />
        </el-tab-pane>

        <el-tab-pane label="库存" name="inventory">
          <InventorySection />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import PartnerList from '../components/PartnerList.vue'
import OrderListView from '../components/OrderListView.vue'
import InventorySection from '../components/InventorySection.vue'
import partnersApi from '../api/partners'

const customersApi = {
  getList: partnersApi.getCustomers,
  create: partnersApi.createCustomer,
  update: partnersApi.updateCustomer,
  delete: partnersApi.deleteCustomer,
}
const suppliersApi = {
  getList: partnersApi.getSuppliers,
  create: partnersApi.createSupplier,
  update: partnersApi.updateSupplier,
  delete: partnersApi.deleteSupplier,
}

const activeTab = ref('customers')
</script>
