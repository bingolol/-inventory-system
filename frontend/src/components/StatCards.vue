<template>
  <div class="row">
    <div v-for="(item, index) in items" :key="index" class="c4">
      <div class="stat-mini">
        <span class="stat-mini-label">{{ item.label }}</span>
        <span class="stat-mini-value" :class="item.valueClass" :style="valueStyle(item)">
          <slot :name="`value-${index}`" :item="item">{{ item.value }}</slot>
        </span>
      </div>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  items: {
    type: Array,
    default: () => []
  }
})

function valueStyle(item) {
  if (item.color) {
    return { color: item.color.startsWith('#') || item.color.startsWith('var(--') ? item.color : `var(--${item.color})` }
  }
  return {}
}
</script>
