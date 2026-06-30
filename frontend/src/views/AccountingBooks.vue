<template>
  <el-card shadow="never">
    <template #header><div class="card-header"><span class="page-title">会计账簿</span></div></template>
    <el-tabs v-model="activeTab">
      <el-tab-pane label="凭证查询" name="journal"><JournalMoves /></el-tab-pane>
      <el-tab-pane label="试算平衡表" name="trial"><TrialBalance /></el-tab-pane>
    </el-tabs>
  </el-card>
</template>

<script setup>
import { ref } from 'vue'
import { useRoute } from 'vue-router'
import JournalMoves from './JournalMoves.vue'
import TrialBalance from './TrialBalance.vue'
const route = useRoute()
const activeTab = ref(route.query.tab === 'trial' ? 'trial' : 'journal')
</script>
