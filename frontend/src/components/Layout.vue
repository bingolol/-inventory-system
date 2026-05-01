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
            <span style="display:flex;justify-content:space-between;">
              <span>{{ acc.name }}</span>
              <el-tag size="small" :type="acc.type === 'company' ? 'primary' : 'success'">{{ acc.type === 'company' ? '公司' : '个人' }}</el-tag>
            </span>
          </el-option>
        </el-select>
      </div>
      <el-menu :default-active="currentRoute" router class="app-menu" background-color="transparent" :active-text-color="'var(--primary)'">
        <template v-if="currentAccount?.type === 'company'">
          <el-menu-item index="/">
            <el-icon><DataAnalysis /></el-icon>
            <span>仪表盘</span>
          </el-menu-item>
          <el-menu-item index="/products">
            <el-icon><Goods /></el-icon>
            <span>商品管理</span>
          </el-menu-item>
          <el-menu-item index="/suppliers">
            <el-icon><OfficeBuilding /></el-icon>
            <span>供应商管理</span>
          </el-menu-item>
          <el-menu-item index="/customers">
            <el-icon><User /></el-icon>
            <span>客户管理</span>
          </el-menu-item>
          <el-menu-item index="/purchases">
            <el-icon><ShoppingCart /></el-icon>
            <span>采购管理</span>
          </el-menu-item>
          <el-menu-item index="/sales">
            <el-icon><Sell /></el-icon>
            <span>销售管理</span>
          </el-menu-item>
          <el-menu-item index="/inventory">
            <el-icon><Box /></el-icon>
            <span>库存管理</span>
            <el-badge v-if="alertCount > 0" :value="alertCount" class="alert-badge" />
          </el-menu-item>
          <el-menu-item index="/opening-balance">
            <el-icon><Money /></el-icon>
            <span>期初余额</span>
          </el-menu-item>
          <el-menu-item index="/projects">
            <el-icon><Document /></el-icon>
            <span>项目管理</span>
          </el-menu-item>
          <el-menu-item index="/reports">
            <el-icon><TrendCharts /></el-icon>
            <span>报表统计</span>
          </el-menu-item>
          <el-menu-item index="/financial-reports">
            <el-icon><Document /></el-icon>
            <span>财务报表</span>
          </el-menu-item>
          <el-menu-item index="/invoices">
            <el-icon><DocumentChecked /></el-icon>
            <span>发票管理</span>
          </el-menu-item>
          <el-menu-item index="/tax-report">
            <el-icon><DataLine /></el-icon>
            <span>税务报表</span>
          </el-menu-item>
          <el-menu-item index="/income-tax-report">
            <el-icon><DataAnalysis /></el-icon>
            <span>企业所得税</span>
          </el-menu-item>
          <el-menu-item index="/cash-flows">
            <el-icon><Money /></el-icon>
            <span>现金流量表</span>
          </el-menu-item>
          <el-menu-item index="/reconciliations">
            <el-icon><DocumentChecked /></el-icon>
            <span>对账管理</span>
          </el-menu-item>
          <el-menu-item index="/expenses">
            <el-icon><Money /></el-icon>
            <span>费用管理</span>
          </el-menu-item>
          <el-menu-item index="/logs">
            <el-icon><Document /></el-icon>
            <span>操作日志</span>
          </el-menu-item>
          <el-menu-item index="/backup">
            <el-icon><FolderChecked /></el-icon>
            <span>数据备份</span>
          </el-menu-item>
        </template>
        <template v-else>
          <el-menu-item index="/personal">
            <el-icon><Wallet /></el-icon>
            <span>流水账</span>
          </el-menu-item>
          <el-menu-item index="/logs">
            <el-icon><Document /></el-icon>
            <span>操作日志</span>
          </el-menu-item>
          <el-menu-item index="/backup">
            <el-icon><FolderChecked /></el-icon>
            <span>数据备份</span>
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
</template>

<script setup>
import { computed, ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../api'
import { accountStore } from '../stores/account'

const route = useRoute()
const router = useRouter()
const currentRoute = computed(() => route.path)
const currentTitle = computed(() => route.meta.title || '仪表盘')
const alertCount = ref(0)
const currentDate = ref('')
const accounts = ref([])
const currentAccountId = computed({
  get: () => Number(accountStore.currentAccountId) || 1,
  set: (val) => accountStore.setCurrentAccount(val)
})

const currentAccount = computed(() => accountStore.currentAccount)

const updateDate = () => {
  const now = new Date()
  currentDate.value = now.toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', weekday: 'short' })
}

const loadAccounts = async () => {
  try {
    accounts.value = await api.getAccounts()
    accountStore.setAccounts(accounts.value)
    if (!accountStore.currentAccountId && accounts.value.length > 0) {
      accountStore.setCurrentAccount(accounts.value[0].id)
    }
  } catch (e) { /* ignore */ }
}

const loadAlertCount = async () => {
  if (currentAccount.value?.type !== 'company') return
  try {
    const data = await api.getAlerts()
    alertCount.value = data.length
  } catch (e) { /* ignore */ }
}

const onAccountChange = (id) => {
  accountStore.setCurrentAccount(id)
  // 如果切换到个人账本但当前在公司页面，或个人账本但当前在个人页面，需要跳转
  const acc = accounts.value.find(a => a.id === id)
  if (acc?.type === 'personal' && !route.path.startsWith('/personal') && route.path !== '/logs') {
    router.push('/personal')
  } else if (acc?.type === 'company' && (route.path === '/personal')) {
    router.push('/')
  } else {
    // 刷新当前页面数据
    router.go(0)
  }
}

watch(() => route.path, () => {
  loadAlertCount()
})

onMounted(() => {
  updateDate()
  loadAccounts().then(() => {
    loadAlertCount()
  })
  setInterval(updateDate, 60000)
  setInterval(loadAlertCount, 30000)
})
</script>

<style scoped>
.app-container {
  height: 100vh;
  overflow: hidden;
}

.app-aside {
  background: #fff;
  border-right: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  overflow-y: auto;
}

.app-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 20px 20px 16px;
  font-size: 18px;
  font-weight: 700;
  color: var(--primary);
}

.app-menu {
  border-right: none;
  padding: 0 8px;
}

.app-menu .el-menu-item {
  border-radius: 8px;
  margin: 4px 0;
  height: 44px;
  line-height: 44px;
}

.app-menu .el-menu-item.is-active {
  background: var(--primary-light) !important;
  font-weight: 600;
}

.app-main {
  background: var(--bg-page);
}

.app-header {
  background: #fff;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 56px !important;
}

.app-header h2 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.header-date {
  font-size: 13px;
  color: var(--text-secondary);
}

.app-content {
  padding: 20px;
  overflow-y: auto;
}

.alert-badge {
  margin-left: 4px;
}
</style>