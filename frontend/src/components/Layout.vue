<template>
  <el-container class="app-container">
    <el-aside width="220px" class="app-aside">
      <div class="app-logo">
        <el-icon :size="28"><Box /></el-icon>
        <span>进销存管理</span>
      </div>
      <!-- 账本切换器 -->
      <div style="padding: 0 12px 12px;">
        <el-select v-model="currentAccountId" size="small" style="width:100%" @change="onAccountChange">
          <el-option v-for="acc in accounts" :key="acc.id" :label="acc.name" :value="acc.id">
            <div style="display:flex;justify-content:space-between;align-items:center;">
              <span>{{ acc.name }}</span>
              <el-tag size="small" :type="acc.type === 'company' ? 'primary' : 'success'">{{ acc.type === 'company' ? '公司' : '个人' }}</el-tag>
            </div>
          </el-option>
        </el-select>
        <div style="display:flex;gap:6px;margin-top:6px;">
          <el-button size="small" :icon="Plus" style="flex:1" @click="openCreateDialog" />
          <el-button size="small" :icon="Edit" style="flex:1" @click="openRenameDialog" />
          <el-button size="small" :icon="Delete" style="flex:1" @click="openDeleteConfirm" />
        </div>
      </div>
      <el-menu :default-active="currentRoute" @select="handleMenuSelect" class="app-menu" background-color="transparent" :active-text-color="'var(--primary)'">
        <template v-for="item in menuItems" :key="item.index">
          <el-sub-menu v-if="item.children" :index="item.index">
            <template #title>
              <el-icon><component :is="item.icon" /></el-icon>
              <span>{{ item.label }}</span>
            </template>
            <el-menu-item v-for="child in item.children" :key="child.index" :index="child.index">
              <el-icon><component :is="child.icon" /></el-icon>
              <span>{{ child.label }}</span>
            </el-menu-item>
          </el-sub-menu>
          <el-menu-item v-else :index="item.index">
            <el-icon><component :is="item.icon" /></el-icon>
            <span>{{ item.label }}</span>
            <el-badge v-if="item.badge === 'alertCount' && alertCount > 0" :value="alertCount" class="alert-badge" />
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>
    <el-container class="app-main">
      <el-header class="app-header">
        <div class="header-left">
          <h2>{{ currentTitle }}</h2>
        </div>
        <div class="header-right">
          <span class="header-date">{{ currentDate }}</span>
        </div>
      </el-header>
      <el-main class="app-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>

  <!-- 账本重命名对话框 -->
  <el-dialog v-model="renameDialogVisible" title="修改账本名称" width="360px" :close-on-click-modal="false">
    <el-input v-model="renameForm.name" placeholder="请输入账本名称" maxlength="50" show-word-limit />
    <template #footer>
      <el-button @click="renameDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="renameLoading" @click="handleRename">确定</el-button>
    </template>
  </el-dialog>

  <!-- 新建账本对话框 -->
  <el-dialog v-model="createDialogVisible" title="新建账本" width="400px" :close-on-click-modal="false">
    <el-form label-width="80px">
      <el-form-item label="账本名称">
        <el-input v-model="createForm.name" placeholder="如：XX公司" maxlength="50" show-word-limit />
      </el-form-item>
      <el-form-item label="账本类型">
        <el-radio-group v-model="createForm.type">
          <el-radio value="company">公司</el-radio>
          <el-radio value="personal">个人</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item label="纳税人类型" v-if="createForm.type === 'company'">
        <el-radio-group v-model="createForm.taxpayer_type">
          <el-radio value="small_scale">小规模纳税人</el-radio>
          <el-radio value="general">一般纳税人</el-radio>
        </el-radio-group>
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="createDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="createLoading" @click="handleCreate">创建</el-button>
    </template>
  </el-dialog>

  <!-- AI危险操作确认对话框 -->
  <ConfirmDialog ref="confirmDialogRef" />
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Edit, Plus, Delete } from '@element-plus/icons-vue'
import accountsApi from '../api/accounts'
import productsApi from '../api/products'
import { useAccountStore } from '../stores/account'
import { companyMenuItems, personalMenuItems } from '../composables/useMenuConfig'
import { useAccountManagement } from '../composables/useAccountManagement'
import ConfirmDialog from './ConfirmDialog.vue'
const accountStore = useAccountStore()
const confirmDialogRef = ref(null)

const route = useRoute()
const router = useRouter()
const currentRoute = computed(() => route.path)
const currentTitle = computed(() => route.meta.title ?? '仪表盘')
const alertCount = ref(0)
const currentDate = ref('')
const accounts = ref([])
const currentAccountId = computed({
  get: () => Number(accountStore.currentAccountId) || 1,
  set: (val) => accountStore.setCurrentAccount(val)
})

const currentAccount = computed(() => accountStore.currentAccount)

// 菜单配置：根据账本类型动态切换
const menuItems = computed(() =>
  currentAccount.value?.type === 'company' ? companyMenuItems : personalMenuItems
)

const updateDate = () => {
  const now = new Date()
  currentDate.value = now.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', weekday: 'short' })
}

const loadAccounts = async () => {
  try {
    accounts.value = await accountsApi.getAccounts()
    accountStore.setAccounts(accounts.value)
    if (!accountStore.currentAccountId && accounts.value.length > 0) {
      accountStore.setCurrentAccount(accounts.value[0].id)
    }
  } catch (e) { console.error('加载账本列表失败:', e) }
}

const loadAlertCount = async () => {
  if (currentAccount.value?.type !== 'company') return
  try {
    const data = await productsApi.getAlerts()
    alertCount.value = data.length
  } catch (e) { console.error('加载库存预警数量失败:', e) }
}

const handleMenuSelect = (index) => {
  if (index !== route.path) {
    router.push(index)
  }
}

const onAccountChange = (id) => {
  accountStore.setCurrentAccount(id)
  const acc = accounts.value.find(a => a.id === id)
  if (acc?.type === 'personal' && !route.path.startsWith('/personal') && route.path !== '/logs') {
    router.push('/personal')
  } else if (acc?.type === 'company' && (route.path === '/personal')) {
    router.push('/')
  }
}

// 账本管理（重建/重命名/删除）
const {
  renameDialogVisible, renameForm, renameLoading, openRenameDialog, handleRename,
  createDialogVisible, createForm, createLoading, openCreateDialog, handleCreate,
  openDeleteConfirm
} = useAccountManagement({ accounts, accountStore, onAccountsChanged: loadAccounts })

watch(() => route.path, () => {
  loadAlertCount()
})

let dateTimer, alertTimer

onMounted(() => {
  updateDate()
  loadAccounts().then(() => {
    loadAlertCount()
  })
  dateTimer = setInterval(updateDate, 60000)
  alertTimer = setInterval(loadAlertCount, 30000)
})

onUnmounted(() => {
  clearInterval(dateTimer)
  clearInterval(alertTimer)
})
</script>

<style scoped>
.app-container {
  height: 100vh;
  overflow: hidden;
}

/* ═══ 侧边栏增强 ═══ */
.app-aside {
  background: linear-gradient(180deg, #ffffff 0%, #fafbfc 100%);
  border-right: 1px solid var(--border-lighter);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.04);
}

/* Logo 区域：更强的品牌感 */
.app-logo {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 24px 20px 20px;
  font-size: 20px;
  font-weight: 700;
  color: var(--primary);
  letter-spacing: -0.5px;
  border-bottom: 1px solid var(--border-lighter);
  background: linear-gradient(135deg, var(--primary-lighter) 0%, transparent 100%);
}

.app-logo .el-icon {
  filter: drop-shadow(0 2px 4px rgba(64, 158, 255, 0.3));
}

/* 菜单项增强：更现代的交互反馈 */
.app-menu {
  border-right: none;
  padding: 12px 12px;
  background: transparent;
}

.app-menu .el-menu-item {
  border-radius: var(--radius-md);
  margin: 6px 0;
  height: 48px;
  line-height: 48px;
  transition: all var(--transition-base);
  font-weight: var(--font-weight-medium);
  position: relative;
  overflow: hidden;
}

.app-menu .el-menu-item::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--primary);
  transform: scaleY(0);
  transition: transform var(--transition-base);
}

.app-menu .el-menu-item:hover {
  background: var(--bg-hover) !important;
  transform: translateX(4px);
}

.app-menu .el-menu-item.is-active {
  background: var(--primary-light) !important;
  font-weight: var(--font-weight-semibold);
  color: var(--primary) !important;
}

.app-menu .el-menu-item.is-active::before {
  transform: scaleY(1);
}

.app-menu .el-menu-item .el-icon {
  margin-right: 12px;
  transition: transform var(--transition-fast);
}

.app-menu .el-menu-item:hover .el-icon {
  transform: scale(1.1);
}

/* 主内容区增强 */
.app-main {
  background: var(--bg-page);
  position: relative;
}

/* 头部增强：更专业的顶部导航 */
.app-header {
  background: linear-gradient(135deg, #ffffff 0%, #fafbfc 100%);
  border-bottom: 1px solid var(--border-lighter);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 32px;
  height: 64px !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
}

.app-header h2 {
  font-size: var(--font-size-xl);
  font-weight: var(--font-weight-bold);
  color: var(--text-primary);
  letter-spacing: -0.3px;
}

.header-date {
  font-size: var(--font-size-sm);
  color: var(--text-secondary);
  font-weight: var(--font-weight-medium);
  padding: 6px 12px;
  background: var(--bg-elevated);
  border-radius: var(--radius-full);
  border: 1px solid var(--border-lighter);
}

/* 内容区优化 */
.app-content {
  padding: 24px;
  overflow-y: auto;
  background: linear-gradient(180deg, var(--bg-page) 0%, #f8f9fa 100%);
}

.alert-badge {
  margin-left: 8px;
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.7;
  }
}

/* 滚动条美化 */
.app-aside::-webkit-scrollbar,
.app-content::-webkit-scrollbar {
  width: 6px;
}

.app-aside::-webkit-scrollbar-thumb,
.app-content::-webkit-scrollbar-thumb {
  background: var(--border-color);
  border-radius: var(--radius-full);
}

.app-aside::-webkit-scrollbar-thumb:hover,
.app-content::-webkit-scrollbar-thumb:hover {
  background: var(--text-secondary);
}
</style>