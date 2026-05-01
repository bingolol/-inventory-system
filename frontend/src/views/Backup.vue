<template>
  <div class="backup-page">
    <el-card shadow="never">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center;">
          <span style="font-size:16px;font-weight:600;">数据热备份</span>
          <el-button type="primary" :loading="backupLoading" @click="doBackup">
            <el-icon><FolderChecked /></el-icon>
            一键备份
          </el-button>
        </div>
      </template>

      <el-alert
        v-if="lastResult"
        :title="lastResult.message"
        :type="lastResult.status === 'ok' ? 'success' : 'error'"
        show-icon
        closable
        style="margin-bottom: 16px;"
      />

      <el-alert
        title="建议每周备份一次，备份文件保存在项目根目录的 hot_backup/ 文件夹中，与数据目录隔离防止误删。"
        type="info"
        :closable="false"
        style="margin-bottom: 20px;"
      />

      <el-table :data="backups" stripe v-loading="listLoading" empty-text="暂无备份">
        <el-table-column label="备份文件" prop="filename" min-width="180" />
        <el-table-column label="大小" width="120">
          <template #default="{ row }">
            {{ row.size_kb >= 1024 ? (row.size_kb / 1024).toFixed(1) + ' MB' : row.size_kb + ' KB' }}
          </template>
        </el-table-column>
        <el-table-column label="备份时间" prop="created_at" width="180" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="{ row }">
            <el-button link type="primary" @click="downloadBackup(row.filename)">
              下载
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import api from '../api'

const backupLoading = ref(false)
const listLoading = ref(false)
const backups = ref([])
const lastResult = ref(null)

const loadBackups = async () => {
  listLoading.value = true
  try {
    backups.value = await api.listBackups()
  } catch (e) {
    console.error('获取备份列表失败:', e)
  } finally {
    listLoading.value = false
  }
}

const doBackup = async () => {
  backupLoading.value = true
  lastResult.value = null
  try {
    const data = await api.hotBackup()
    lastResult.value = data
    await loadBackups()
  } catch (e) {
    lastResult.value = {
      status: 'error',
      message: e.response?.data?.detail || '热备份失败'
    }
  } finally {
    backupLoading.value = false
  }
}

const downloadBackup = (filename) => {
  const url = api.getBackupDownloadUrl(filename)
  window.open(url, '_blank')
}

onMounted(() => {
  loadBackups()
})
</script>

<style scoped>
.backup-page {
  max-width: 800px;
}
</style>