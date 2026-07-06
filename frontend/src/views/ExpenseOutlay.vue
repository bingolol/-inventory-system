<template>
  <el-card shadow="never">
    <template #header><div class="card-header"><span class="page-title">费用支出</span></div></template>
    <el-tabs v-model="activeTab">
      <el-tab-pane label="费用管理" name="expenses"><Expenses /></el-tab-pane>
      <el-tab-pane label="个人垫付" name="advances"><PersonalAdvances /></el-tab-pane>
    </el-tabs>
  </el-card>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import Expenses from './Expenses.vue'
import PersonalAdvances from './PersonalAdvances.vue'
const route = useRoute()
const activeTab = ref(route.query.tab === 'advances' ? 'advances' : 'expenses')
</script>
