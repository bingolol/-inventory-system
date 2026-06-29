<template>
  <div class="mg-card" :style="{ '--card-color': color }">
    <div class="mg-card-icon" :style="{ background: bg }">
      <el-icon :size="22" :color="color"><component :is="icon" /></el-icon>
    </div>
    <div class="mg-card-title">{{ title }}</div>
    <div class="mg-card-stat">
      <div class="mg-card-stat-value">{{ prefix }}{{ formatMoney(mainValue) }}</div>
      <div class="mg-card-stat-label">{{ mainLabel }}</div>
    </div>
    <div v-if="loading" class="mg-loading">
      <div class="mg-skeleton-line" v-for="i in 3" :key="i"></div>
    </div>
    <div v-else class="mg-card-list">
      <div v-for="(item, idx) in items" :key="idx" class="mg-card-item">
        <span class="mg-item-label">{{ item.label }}</span>
        <span class="mg-item-value" :class="{ 'mg-warn': item.warning }">
          {{ typeof item.value === 'number' ? formatMoney(item.value) : item.value }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { formatMoney } from '../utils/format'

defineProps({
  icon: { type: [String, Object], required: true },
  title: { type: String, required: true },
  color: { type: String, default: '#409EFF' },
  bg: { type: String, default: 'rgba(64,158,255,0.08)' },
  mainValue: { type: [Number, String], default: 0 },
  prefix: { type: String, default: '¥' },
  mainLabel: { type: String, default: '' },
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false }
})
</script>

<style scoped>
.mg-card {
  background: var(--bg-card);
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.04);
  border: 1px solid var(--border-lighter);
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}
.mg-card:hover {
  box-shadow: 0 8px 32px rgba(0,0,0,0.08);
  transform: translateY(-2px);
}
.mg-card-icon {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 16px;
}
.mg-card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 16px;
}
.mg-card-stat {
  margin-bottom: 16px;
}
.mg-card-stat-value {
  font-size: 30px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.5px;
  line-height: 1.2;
}
.mg-card-stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 2px;
}
.mg-card-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding-top: 16px;
  border-top: 1px solid var(--border-lighter);
}
.mg-card-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}
.mg-item-label {
  color: var(--text-secondary);
}
.mg-item-value {
  font-weight: 600;
  color: var(--text-regular);
  font-family: 'Consolas', 'Monaco', monospace;
}
.mg-warn {
  color: var(--el-color-danger);
}
.mg-loading {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding-top: 16px;
}
.mg-skeleton-line {
  height: 14px;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--border-lighter) 25%, var(--bg-elevated) 50%, var(--border-lighter) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
.mg-skeleton-line:nth-child(1) { width: 90%; }
.mg-skeleton-line:nth-child(2) { width: 70%; }
.mg-skeleton-line:nth-child(3) { width: 80%; }
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
