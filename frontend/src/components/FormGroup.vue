<template>
  <div class="fg" :style="groupStyle">
    <div class="fgh">
      <span class="fgt" :style="tagStyle">{{ title }}</span>
    </div>
    <div class="fgb">
      <slot />
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
  color: { type: String, default: 'primary' }
})

const groupStyle = computed(() => ({
  borderLeftColor: colorVar(props.color)
}))

const tagStyle = computed(() => ({
  background: lightVar(props.color),
  color: colorVar(props.color)
}))

function colorVar(name) {
  return `var(--${name})`
}

function lightVar(name) {
  return `var(--${name}-light)`
}
</script>
