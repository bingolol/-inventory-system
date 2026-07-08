<template>
  <div class="ff">
    <span class="fl" :style="labelStyle">{{ label }}</span>
    <div class="fc">
      <slot />
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  label: { type: String, required: true },
  labelWidth: { type: String, default: '70px' }
})

const labelStyle = {
  minWidth: props.labelWidth
}
</script>
