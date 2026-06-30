<template>
  <el-card shadow="never">
    <template #header><div class="card-header"><span class="page-title">伙伴管理</span></div></template>
    <el-tabs v-model="activeTab">
      <el-tab-pane label="客户" name="customers"><Customers /></el-tab-pane>
      <el-tab-pane label="供应商" name="suppliers"><Suppliers /></el-tab-pane>
    </el-tabs>
  </el-card>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import Customers from './Customers.vue'
import Suppliers from './Suppliers.vue'
const route = useRoute()
const activeTab = ref(route.query.tab === 'suppliers' ? 'suppliers' : 'customers')
</script>
