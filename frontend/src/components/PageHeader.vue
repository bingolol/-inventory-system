<template>
  <div class="card-header" data-testid="page-header">
    <span class="page-title" data-testid="page-title">{{ title }}</span>
    <div class="card-header-actions" data-testid="page-header-actions">
      <slot name="actions" />
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true }
})
</script>
