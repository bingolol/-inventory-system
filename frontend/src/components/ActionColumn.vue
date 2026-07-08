<template>
  <div class="action-column">
    <template v-for="action in visibleActions" :key="action.key">
      <el-popconfirm
        v-if="action.confirm"
        :title="action.confirm"
        @confirm="handleClick(action)"
      >
        <template #reference>
          <el-button
            size="small"
            :type="action.type || 'primary'"
            :link="action.link !== false"
            :disabled="isDisabled(action)"
            :data-testid="`action-${action.key}`"
          >
            {{ action.label }}
          </el-button>
        </template>
      </el-popconfirm>
      <el-button
        v-else
        size="small"
        :type="action.type || 'primary'"
        :link="action.link !== false"
        :disabled="isDisabled(action)"
        :data-testid="`action-${action.key}`"
        @click="handleClick(action)"
      >
        {{ action.label }}
      </el-button>
    </template>

    <el-dropdown v-if="moreActions.length" size="small">
      <el-button size="small" link>
        <el-icon><More /></el-icon>
      </el-button>
      <template #dropdown>
        <el-dropdown-menu>
          <el-dropdown-item
            v-for="action in moreActions"
            :key="action.key"
            :disabled="isDisabled(action)"
            @click="handleClick(action)"
          >
            {{ action.label }}
          </el-dropdown-item>
        </el-dropdown-menu>
      </template>
    </el-dropdown>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { More } from '@element-plus/icons-vue'

const props = defineProps({
  actions: {
    type: Array,
    required: true
  }
})

const emit = defineEmits(['click'])

const visibleActions = computed(() =>
  props.actions.filter(a => !a.more && resolveShow(a))
)

const moreActions = computed(() =>
  props.actions.filter(a => a.more && resolveShow(a))
)

function resolveShow(action) {
  if (typeof action.show === 'function') return action.show()
  return action.show !== false
}

function isDisabled(action) {
  if (typeof action.disabled === 'function') return action.disabled()
  return !!action.disabled
}

function handleClick(action) {
  emit('click', action.key, action)
}
</script>

<style scoped>
.action-column {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}
</style>
