<template>
  <el-container class="app-shell">
    <aside class="side">
      <div class="side-hd">
        <div class="side-nm">进销存</div>
        <div class="side-sub">v2.0</div>
      </div>
      <div class="side-acct">
        <el-select v-model="currentAccountId" size="small" class="acct-sl" @change="onAccountChange">
          <el-option v-for="acc in accounts" :key="acc.id" :label="acc.name" :value="acc.id" />
        </el-select>
        <div class="side-acct-acts">
          <span class="sa-btn" title="新建账本" @click="openCreateDialog">＋</span>
          <span class="sa-btn" title="重命名" @click="openRenameDialog">✎</span>
          <span class="sa-btn" title="删除" @click="openDeleteConfirm">−</span>
        </div>
      </div>
      <nav class="side-nav">
        <template v-for="item in menuItems" :key="item.index">
          <div class="sg" v-if="item.children">
            <div class="sgt">{{ item.label }}</div>
            <a class="si" v-for="ch in item.children" :key="ch.index" :class="{ active: currentRoute === ch.index }" @click="handleMenuSelect(ch.index)">
              <span class="si-ic">{{ iconMap[ch.icon] || '◻' }}</span><span>{{ ch.label }}</span>
            </a>
          </div>
          <a v-else class="si" :class="{ active: currentRoute === item.index }" @click="handleMenuSelect(item.index)">
            <span class="si-ic">{{ iconMap[item.icon] || '◉' }}</span><span>{{ item.label }}</span>
          </a>
        </template>
      </nav>
    </aside>
    <el-container class="app-main">
      <el-header class="app-bar">
        <div class="app-bar-left">
          <h2 class="app-bar-title">{{ currentTitle }}</h2>
          <span class="app-bar-desc" v-if="currentDesc">{{ currentDesc }}</span>
        </div>
        <div class="app-bar-right">
          <span class="app-bar-date">{{ currentDate }}</span>
        </div>
      </el-header>
      <el-main class="app-body"><router-view /></el-main>
    </el-container>
  </el-container>

  <el-dialog v-model="renameDialogVisible" title="修改账本名称" width="360px">
    <el-input v-model="renameForm.name" placeholder="请输入账本名称" maxlength="50" show-word-limit />
    <template #footer>
      <el-button @click="renameDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="renameLoading" @click="handleRename">确定</el-button>
    </template>
  </el-dialog>

  <el-dialog v-model="createDialogVisible" title="新建账本" width="400px">
    <el-form label-width="80px">
      <el-form-item label="账本名称"><el-input v-model="createForm.name" placeholder="如：XX公司" maxlength="50" show-word-limit /></el-form-item>
      <el-form-item label="账本类型"><el-radio-group v-model="createForm.type"><el-radio value="company">公司</el-radio><el-radio value="personal">个人</el-radio></el-radio-group></el-form-item>
      <el-form-item label="纳税人类型" v-if="createForm.type === 'company'"><el-radio-group v-model="createForm.taxpayer_type"><el-radio value="small_scale">小规模纳税人</el-radio><el-radio value="general">一般纳税人</el-radio></el-radio-group></el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="createDialogVisible = false">取消</el-button>
      <el-button type="primary" :loading="createLoading" @click="handleCreate">创建</el-button>
    </template>
  </el-dialog>

  <ConfirmDialog ref="confirmDialogRef" />
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
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
const currentDesc = computed(() => route.meta.desc ?? '')

const iconMap = {
  DataAnalysis: '◉', Sell: '◻', Box: '◻', DataBoard: '◉', Wallet: '◻',
  TrendCharts: '◻', Ticket: '◻', Files: '◻', Document: '◻', DocumentChecked: '◻',
  DataLine: '◻', Goods: '◻', OfficeBuilding: '◻', User: '◻', ShoppingCart: '◻',
  FolderChecked: '◻'
}

const alertCount = ref(0)
const currentDate = ref('')
const accounts = ref([])

const currentAccountId = computed({
  get: () => Number(accountStore.currentAccountId) || 1,
  set: (val) => accountStore.setCurrentAccount(val)
})
const currentAccount = computed(() => accountStore.currentAccount)
const menuItems = computed(() => currentAccount.value?.type === 'company' ? companyMenuItems : personalMenuItems)

const updateDate = () => { currentDate.value = new Date().toLocaleDateString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', weekday: 'short' }) }

const loadAccounts = async () => {
  try {
    accounts.value = await accountsApi.getAccounts()
    accountStore.setAccounts(accounts.value)
    if (!accountStore.currentAccountId && accounts.value.length > 0) accountStore.setCurrentAccount(accounts.value[0].id)
  } catch (e) { console.error('加载账本列表失败:', e) }
}

const handleMenuSelect = (index) => { if (index !== route.path) router.push(index) }

const onAccountChange = (id) => {
  accountStore.setCurrentAccount(id)
  const acc = accounts.value.find(a => a.id === id)
  if (acc?.type === 'personal' && !route.path.startsWith('/personal') && route.path !== '/logs') router.push('/personal')
  else if (acc?.type === 'company' && route.path === '/personal') router.push('/')
}

const { renameDialogVisible, renameForm, renameLoading, openRenameDialog, handleRename, createDialogVisible, createForm, createLoading, openCreateDialog, handleCreate, openDeleteConfirm } = useAccountManagement({ accounts, accountStore, onAccountsChanged: loadAccounts })

watch(() => route.path, () => {})
let dateTimer
onMounted(() => { updateDate(); loadAccounts(); dateTimer = setInterval(updateDate, 60000) })
onUnmounted(() => { clearInterval(dateTimer) })
</script>

<style scoped>
.app-shell { height: 100vh; overflow: hidden; }

/* Sidebar — 200px white, clean */
.side {
  width: 200px; flex-shrink: 0;
  background: #fff; border-right: 1px solid #edf0f5;
  display: flex; flex-direction: column; overflow-y: auto;
}
.side-hd { padding: 20px 16px 14px; border-bottom: 1px solid #f5f6f8; }
.side-nm { font-size: 15px; font-weight: 700; color: #1d2129; }
.side-sub { font-size: 11px; color: #86909c; margin-top: 1px; }
.side-acct { padding: 8px 10px; border-bottom: 1px solid #f5f6f8; }
.side-acct-acts { display: flex; gap: 4px; margin-top: 6px; }
.sa-btn { flex:1; display:flex; align-items:center; justify-content:center; padding:3px 0; border:1px solid #edf0f5; border-radius:4px; font-size:13px; color:#4e5969; cursor:pointer; background:#fff; }
.sa-btn:hover { background:#f5f6f8; }
.acct-sl { width: 100%; }
.side-nav { padding: 4px 6px; flex: 1; overflow-y: auto; }
.sgt { font-size: 10px; font-weight: 600; color: #86909c; padding: 10px 10px 3px; letter-spacing: 1px; }
.si { display: flex; align-items: center; gap: 8px; padding: 6px 10px; border-radius: 6px; font-size: 13px; color: #4e5969; cursor: pointer; text-decoration: none; margin: 1px 0; }
.si:hover { background: #f5f6f8; color: #1d2129; }
.si.active { background: #f0f2f5; color: #1d2129; font-weight: 600; }
.si-ic { font-size: 14px; width: 18px; text-align: center; }

/* Header — 48px */
.app-bar {
  background: #fff; border-bottom: 1px solid #edf0f5;
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 24px; height: 48px !important; position: sticky; top: 0; z-index: 100;
}
.app-bar-left { display: flex; align-items: center; gap: 10px; }
.app-bar-title { font-size: 14px; font-weight: 600; color: #1d2129; }
.app-bar-desc { font-size: 12px; color: #c9cdd4; }
.app-bar-date { font-size: 12px; color: #86909c; background: #f5f6f8; padding: 2px 10px; border-radius: 4px; }

/* Content */
.app-body { padding: 24px; overflow-y: auto; background: #f8f9fa; }

/* Scrollbar */
.side::-webkit-scrollbar { width: 4px; }
.side::-webkit-scrollbar-thumb { background: #edf0f5; border-radius: 4px; }
.app-body::-webkit-scrollbar { width: 6px; }
.app-body::-webkit-scrollbar-thumb { background: #d0d5dd; border-radius: 4px; }
</style>
