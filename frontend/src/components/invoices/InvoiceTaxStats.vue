<template>
  <div class="inv-stats">
    <div class="inv-stat-item">
      <span class="inv-stat-label">销项税额</span>
      <span class="inv-stat-value c-primary">{{ formatMoney(outputTax) }}</span>
    </div>
    <div class="inv-stat-item">
      <span class="inv-stat-label">进项税额</span>
      <span class="inv-stat-value c-success">{{ formatMoney(inputTax) }}</span>
    </div>
    <div class="inv-stat-item">
      <span class="inv-stat-label">应纳税额</span>
      <span class="inv-stat-value c-danger">{{ formatMoney(taxPayable) }}</span>
    </div>
  </div>
</template>

<script setup>
import { formatMoney } from '../../utils/format'

defineProps({
  outputTax: { type: Number, default: 0 },
  inputTax: { type: Number, default: 0 },
  taxPayable: { type: Number, default: 0 }
})
</script>

<style scoped>
.inv-stats {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
}
.inv-stat-item {
  flex: 1;
  background: var(--bg-card);
  border: 1px solid var(--border-light);
  border-left: 4px solid var(--primary);
  border-radius: 12px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.inv-stat-label {
  font-size: 12px;
  color: var(--text-secondary);
  font-weight: 500;
  letter-spacing: 0.5px;
}
.inv-stat-value {
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.5px;
}
</style>
