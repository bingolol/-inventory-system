<template>
  <div class="filter-bar" data-testid="filter-bar" :style="barStyle">
    <div class="filter-bar-fields" data-testid="filter-bar-fields">
      <slot />
    </div>
    <div class="filter-bar-actions" data-testid="filter-bar-actions">
      <el-button type="primary" data-testid="filter-search" @click="$emit('search')">
        <el-icon><Search /></el-icon> 查询
      </el-button>
      <el-button data-testid="filter-reset" @click="$emit('reset')">重置</el-button>
      <slot name="extra-actions" />
    </div>
  </div>
</template>

<script setup>
import { Search } from '@element-plus/icons-vue'

defineProps({
  compact: { type: Boolean, default: false }
})

defineEmits(['search', 'reset'])

const barStyle = {
  marginBottom: '16px'
}
</script>

<style scoped>
.filter-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.filter-bar-fields {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: center;
}
.filter-bar-actions {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-left: auto;
}
</style>
