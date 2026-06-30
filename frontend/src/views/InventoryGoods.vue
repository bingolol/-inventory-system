<template>
  <el-card shadow="never">
    <template #header><div class="card-header"><span class="page-title">库存商品</span></div></template>
    <el-tabs v-model="activeTab">
      <el-tab-pane label="商品目录" name="products"><Products /></el-tab-pane>
      <el-tab-pane label="库存明细" name="inventory"><Inventory /></el-tab-pane>
    </el-tabs>
  </el-card>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import Products from './Products.vue'
import Inventory from './Inventory.vue'
const route = useRoute()
const activeTab = ref(route.query.tab === 'inventory' ? 'inventory' : 'products')
</script>
