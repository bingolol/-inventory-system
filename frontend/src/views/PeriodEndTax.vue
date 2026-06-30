<template>
  <el-card shadow="never">
    <template #header><div class="card-header"><span class="page-title">期末税务</span></div></template>
    <el-tabs v-model="activeTab">
      <el-tab-pane label="税务报表" name="tax"><TaxReport /></el-tab-pane>
      <el-tab-pane label="期末处理" name="close"><MonthClose /></el-tab-pane>
    </el-tabs>
  </el-card>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import TaxReport from './TaxReport.vue'
import MonthClose from './MonthClose.vue'
const route = useRoute()
const activeTab = ref(route.query.tab === 'close' ? 'close' : 'tax')
</script>
