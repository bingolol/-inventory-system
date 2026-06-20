<template>
  <div class="tax-report-container">
    <el-card shadow="never">
      <template #header>
        <span class="page-title">税务报表</span>
      </template>

      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <!-- 增值税报表 Tab -->
        <el-tab-pane label="增值税报表" name="vat">
          <VATReportSection />
        </el-tab-pane>

        <!-- 企业所得税 Tab -->
        <el-tab-pane label="企业所得税" name="income-tax">
          <IncomeTaxReportSection />
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import VATReportSection from '../components/VATReportSection.vue'
import IncomeTaxReportSection from '../components/IncomeTaxReportSection.vue'

const activeTab = ref('vat')

const handleTabChange = (tab) => {
  activeTab.value = tab
}
</script>

<style scoped>
.tax-report-container {
  padding: 0;
}
</style>
