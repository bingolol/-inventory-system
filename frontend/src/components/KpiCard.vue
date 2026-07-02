<template>
  <div class="kpi-card" :class="{ 'kpi-clickable': clickable }" :style="borderStyle" @click="$emit('click')">
    <div class="kpi-label">{{ label }}</div>
    <div class="kpi-value" :style="valueStyle">{{ value }}</div>
    <div v-if="$slots.default" class="kpi-slots"><slot /></div>
    <div v-if="hint" class="kpi-hint">{{ hint }}</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], required: true },
  color: { type: String, default: 'var(--text-primary)' },
  borderColor: { type: String, default: 'var(--primary)' },
  hint: { type: String, default: '' },
  clickable: { type: Boolean, default: false },
})

defineEmits(['click'])

const borderStyle = computed(() => ({
  borderLeft: `3px solid ${props.borderColor}`,
}))

const valueStyle = computed(() => ({
  color: props.color,
}))
</script>

<style scoped>
.kpi-card {
  flex: 1;
  background: var(--bg-card);
  border: 1px solid var(--border-lighter);
  border-radius: 10px;
  padding: 14px 16px;
  min-width: 0;
}

.kpi-clickable {
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.kpi-clickable:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.kpi-label {
  font-size: 12px;
  color: var(--text-regular);
  font-weight: 500;
  margin-bottom: 4px;
}

.kpi-value {
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.5px;
  line-height: 1.2;
  margin-bottom: 2px;
  word-break: break-all;
}

.kpi-slots {
  margin-top: 6px;
}

.kpi-hint {
  font-size: 12px;
  color: var(--text-secondary);
}
</style>
