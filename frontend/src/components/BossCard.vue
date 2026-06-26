<template>
  <div
    class="boss-card"
    :style="{
      '--card-accent': accentColor,
      '--card-gradient': `linear-gradient(135deg, ${accentColor}15, ${accentColor}08)`
    }"
  >
    <div class="card-accent-bar"></div>
    <div class="card-body">
      <div class="card-header-area">
        <el-icon :size="22" :color="accentColor"><component :is="icon" /></el-icon>
        <span class="card-title">{{ title }}</span>
      </div>
      <div class="card-main-value">
        <span class="main-number">{{ prefix }}{{ formatMoney(mainValue) }}</span>
        <span class="main-unit">{{ mainUnit }}</span>
      </div>
      <div v-if="loading" class="card-skeleton">
        <div class="skeleton-line" v-for="i in 4" :key="i"></div>
      </div>
      <div v-else-if="items && items.length" class="card-details">
        <div v-for="(item, idx) in items" :key="idx" class="detail-row">
          <span class="detail-label">{{ item.label }}</span>
          <span :class="['detail-value', { 'detail-warning': item.warning }]">
            {{ typeof item.value === 'number' ? formatMoney(item.value) : item.value }}
          </span>
        </div>
      </div>
      <div v-else class="card-empty">暂无数据</div>
    </div>
  </div>
</template>

<script setup>
import { formatMoney } from '../utils/format'

defineProps({
  icon: { type: [String, Object], required: true },
  title: { type: String, required: true },
  accentColor: { type: String, default: '#409EFF' },
  mainValue: { type: [Number, String], default: 0 },
  prefix: { type: String, default: '¥' },
  mainUnit: { type: String, default: '' },
  items: { type: Array, default: null },
  loading: { type: Boolean, default: false }
})
</script>

<style scoped>
.boss-card {
  background: var(--bg-card);
  border: 1px solid var(--border-lighter);
  border-radius: 12px;
  display: flex;
  overflow: hidden;
  transition: all 0.3s ease;
  box-shadow: var(--shadow-sm);
}
.boss-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.08);
}
.card-accent-bar {
  width: 4px;
  flex-shrink: 0;
  background: var(--card-accent);
  border-radius: 4px 0 0 4px;
}
.card-body {
  flex: 1;
  padding: 20px 24px;
}
.card-header-area {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
}
.card-title {
  font-size: var(--font-size-sm);
  font-weight: var(--font-weight-semibold);
  color: var(--text-secondary);
  letter-spacing: 0.3px;
}
.card-main-value {
  margin-bottom: 16px;
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.main-number {
  font-size: 32px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.5px;
  line-height: 1.1;
}
.main-unit {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
}
.card-details {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}
.detail-label {
  color: var(--text-secondary);
}
.detail-value {
  font-weight: var(--font-weight-medium);
  color: var(--text-primary);
  font-family: 'Consolas', 'Monaco', monospace;
}
.detail-warning {
  color: var(--el-color-danger);
}
.card-empty {
  font-size: 13px;
  color: var(--text-placeholder);
  padding: 8px 0;
}
.card-skeleton {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.skeleton-line {
  height: 14px;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--bg-hover) 25%, var(--bg-elevated) 50%, var(--bg-hover) 75%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite;
}
.skeleton-line:nth-child(1) { width: 90%; }
.skeleton-line:nth-child(2) { width: 75%; }
.skeleton-line:nth-child(3) { width: 60%; }
.skeleton-line:nth-child(4) { width: 80%; }
@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}
</style>
