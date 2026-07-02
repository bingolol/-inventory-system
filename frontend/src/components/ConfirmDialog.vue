<template>
  <!-- AI危险操作确认对话框 -->
  <el-dialog
    v-model="visible"
    title="操作确认"
    width="480px"
    :close-on-click-modal="false"
    :close-on-press-escape="false"
    :show-close="false"
    destroy-on-close
  >
    <div class="confirm-body">
      <el-alert type="warning" :closable="false" show-icon>
        <template #title>
          <span>AI 请求执行危险操作，需要您的确认</span>
        </template>
      </el-alert>
      <div class="confirm-detail">
        <div class="detail-row" v-for="item in pendingItems" :key="item.confirm_token">
          <el-tag :type="item.method === 'DELETE' ? 'danger' : 'warning'" size="small">
            {{ item.method }}
          </el-tag>
          <span class="detail-summary">{{ item.summary }}</span>
          <div class="detail-actions">
            <el-button size="small" type="danger" @click="handleConfirm(item)" :loading="item._loading">
              确认执行
            </el-button>
            <el-button size="small" @click="handleCancel(item)">
              取消
            </el-button>
          </div>
        </div>
      </div>
    </div>
    <template #footer>
      <el-button @click="handleCancelAll">全部取消</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import api from '../api/index'
import { useAccountStore } from '../stores/account'
import { handleError } from '../utils/errorHandler'

const visible = ref(false)
const pendingItems = ref([])

let pollTimer = null

// 轮询获取待确认列表
const pollPending = async () => {
  const accountStore = useAccountStore()
  if (!accountStore.currentAccountId && accountStore.accounts.length === 0) return
  try {
    const res = await api.get('/confirm/pending')
    const items = res.pending || []
    // 合并：保留已有的 _loading 状态
    const loadingMap = {}
    for (const item of pendingItems.value) {
      if (item._loading) loadingMap[item.confirm_token] = true
    }
    pendingItems.value = items.map(item => ({
      ...item,
      _loading: loadingMap[item.confirm_token] || false
    }))
    visible.value = pendingItems.value.length > 0
  } catch (e) {
    console.error('轮询待确认请求失败:', e)
  }
}

// 确认执行
const handleConfirm = async (item) => {
  item._loading = true
  try {
    const res = await api.post(`/confirm/${item.confirm_token}`)
    ElMessage.success(`${item.summary} 执行成功`)
    // 从列表中移除
    pendingItems.value = pendingItems.value.filter(i => i.confirm_token !== item.confirm_token)
    visible.value = pendingItems.value.length > 0
  } catch (e) {
    handleError(e, { defaultMsg: '执行失败，请检查该操作是否符合业务规则' })
  } finally {
    item._loading = false
  }
}

// 取消单个
const handleCancel = async (item) => {
  try {
    await api.delete(`/confirm/${item.confirm_token}`)
    ElMessage.info(`已取消: ${item.summary}`)
    pendingItems.value = pendingItems.value.filter(i => i.confirm_token !== item.confirm_token)
    visible.value = pendingItems.value.length > 0
  } catch (e) {
    handleError(e, { defaultMsg: '取消失败，请检查网络连接' })
  }
}

// 全部取消
const handleCancelAll = async () => {
  const tokens = pendingItems.value.map(i => i.confirm_token)
  for (const token of tokens) {
    try {
      await api.delete(`/confirm/${token}`)
    } catch (e) { /* ignore */ }
  }
  pendingItems.value = []
  visible.value = false
  ElMessage.info('已取消全部待确认操作')
}

// 暴露给外部：收到 202 时手动触发轮询
const triggerPoll = () => {
  pollPending()
}

defineExpose({ triggerPoll })

onMounted(() => {
  // 每 3 秒轮询一次
  pollPending()
  pollTimer = setInterval(pollPending, 3000)
  // 暴露轮询方法给全局，让 axios 拦截器收到 202 时可以触发
  window.__confirmDialogPoll = pollPending
})

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
  window.__confirmDialogPoll = null
})
</script>

<style scoped>
.confirm-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.confirm-detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 300px;
  overflow-y: auto;
}
.detail-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: var(--el-fill-color-light);
  border-radius: 6px;
}
.detail-summary {
  flex: 1;
  font-size: 14px;
}
.detail-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
}
</style>