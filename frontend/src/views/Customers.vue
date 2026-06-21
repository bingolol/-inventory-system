<template>
  <PartnerList
    title="客户列表"
    search-placeholder="搜索客户名称"
    name-label="客户名称"
    add-label="新增客户"
    add-title="新增客户"
    edit-title="编辑客户"
    :api="partnerApi"
  />
</template>

<script setup>
import partnersApi from '../api/partners'
import PartnerList from '../components/PartnerList.vue'

const partnerApi = {
  getList: partnersApi.getCustomers,
  create: partnersApi.createCustomer,
  update: partnersApi.updateCustomer,
  delete: partnersApi.deleteCustomer
}
</script>
