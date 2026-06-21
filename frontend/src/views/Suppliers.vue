<template>
  <PartnerList
    title="供应商列表"
    search-placeholder="搜索供应商名称"
    name-label="供应商名称"
    add-label="新增供应商"
    add-title="新增供应商"
    edit-title="编辑供应商"
    :api="partnerApi"
  />
</template>

<script setup>
import partnersApi from '../api/partners'
import PartnerList from '../components/PartnerList.vue'

const partnerApi = {
  getList: partnersApi.getSuppliers,
  create: partnersApi.createSupplier,
  update: partnersApi.updateSupplier,
  delete: partnersApi.deleteSupplier
}
</script>
