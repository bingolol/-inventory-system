<template>
  <div class="fixed-assets-tab">
    <AccountingTip page="assets" />
    <div class="row" style="margin-bottom:12px;">
      <div class="c4"><div class="stat-mini"><span class="stat-mini-label">资产原值</span><span class="stat-mini-value" style="color:var(--primary);">¥{{ formatMoney(totalOriginal) }}</span></div></div>
      <div class="c4"><div class="stat-mini"><span class="stat-mini-label">累计折旧</span><span class="stat-mini-value" style="color:var(--warning);">¥{{ formatMoney(totalDepreciation) }}</span></div></div>
      <div class="c4"><div class="stat-mini"><span class="stat-mini-label">资产净值</span><span class="stat-mini-value" style="color:var(--success);">¥{{ formatMoney(totalNet) }}</span></div></div>
    </div>
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <span class="page-title">固定资产管理</span>
          <div>
            <span style="font-size:12px;color:var(--text-placeholder);margin-right:8px;">折旧期间</span>
            <el-date-picker v-model="depreciatePeriod" type="month" value-format="YYYY-MM" style="width:140px;" />
            <el-button size="small" @click="handleBatchDepreciate" :loading="depreciating">计提折旧</el-button>
            <el-button type="primary" @click="showCreate()"><el-icon><Plus /></el-icon> 新增资产</el-button>
          </div>
        </div>
      </template>
      <div class="filter-bar">
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width:120px" @change="loadData">
          <el-option label="在用" value="在用" />
          <el-option label="停用" value="停用" />
          <el-option label="报废" value="报废" />
        </el-select>
      </div>
      <el-table :data="list" stripe style="width:100%" v-loading="loading">
        <template #empty>
          <el-empty description="暂无固定资产" />
        </template>
        <el-table-column prop="asset_code" label="资产编码" min-width="130" />
        <el-table-column prop="name" label="资产名称" min-width="120" />
        <el-table-column prop="category" label="类别" min-width="100" align="center">
          <template #default="{ row }">            <span class="status-badge" v-if="row.category">{{ row.category }}</span><span v-else>-</span></template>
        </el-table-column>
        <el-table-column prop="original_value" label="原值" min-width="120" align="right"><template #default="{ row }"><span class="money">¥{{ formatMoney(row.original_value) }}</span></template></el-table-column>
        <el-table-column prop="salvage_rate" label="残值率" min-width="80" align="center"><template #default="{ row }">{{ (Number(row.salvage_rate) * 100).toFixed(0) }}%</template></el-table-column>
        <el-table-column prop="useful_life" label="使用寿命(月)" min-width="110" align="center" />
        <el-table-column prop="depreciation_method" label="折旧方法" min-width="110" align="center" />
        <el-table-column prop="start_date" label="开始日期" min-width="110" />
        <el-table-column prop="accumulated_depreciation" label="累计折旧" min-width="120" align="right"><template #default="{ row }"><span class="money">¥{{ formatMoney(row.accumulated_depreciation) }}</span></template></el-table-column>
        <el-table-column label="净值" min-width="120" align="right"><template #default="{ row }"><span class="money">¥{{ formatMoney(Number(row.original_value) - Number(row.accumulated_depreciation)) }}</span></template></el-table-column>
        <el-table-column prop="status" label="状态" min-width="80" align="center"><template #default="{ row }"><span class="status-badge" :class="statusType(row.status)">{{ row.status }}</span></template></el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button v-if="row.status !== '报废'" size="small" link type="primary" @click="showEdit(row)">编辑</el-button>
            <el-button v-if="row.status==='在用'" size="small" link type="success" @click="handleDepreciate(row)">计提折旧</el-button>
            <el-button v-if="row.status !== '报废'" size="small" link type="warning" @click="showDispose(row)">处置</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="dialogVisible" :title="isEdit ? '编辑固定资产' : '新增固定资产'" width="680px" destroy-on-close>
      <el-form :model="form" label-width="0">
        <div class="fa-group" style="border-left-color:var(--primary);">
          <div class="fa-group-header">
            <span class="fa-group-tag" style="background:var(--primary-light);color:var(--primary);">基本信息</span>
          </div>
          <div class="fa-group-body">
            <div class="fa-field"><span class="fa-label" style="min-width:80px;">资产编码</span><el-input v-model="form.asset_code" placeholder="如 FA-001" /></div>
            <div class="fa-field"><span class="fa-label" style="min-width:80px;">资产名称</span><el-input v-model="form.name" placeholder="如 办公电脑" /></div>
            <div class="fa-field"><span class="fa-label" style="min-width:80px;">资产类别</span><el-input v-model="form.category" placeholder="如 电子设备" /></div>
          </div>
        </div>
        <div class="fa-group" style="border-left-color:var(--warning);">
          <div class="fa-group-header">
            <span class="fa-group-tag" style="background:var(--warning-light);color:var(--warning);">财务参数</span>
          </div>
          <div class="fa-group-body">
            <div class="fa-field"><span class="fa-label" style="min-width:100px;">原值</span><el-input-number v-model="form.original_value" :min="0" :precision="2" style="width:100%" controls-position="right" /></div>
            <div class="fa-field"><span class="fa-label" style="min-width:100px;">残值率</span><el-input-number v-model="form.salvage_rate" :min="0" :max="1" :precision="2" :step="0.01" style="width:100%" controls-position="right" /></div>
            <div class="fa-field"><span class="fa-label" style="min-width:100px;">使用寿命</span><el-input-number v-model="form.useful_life" :min="1" style="width:100%" controls-position="right" /></div>
            <div class="fa-field"><span class="fa-label" style="min-width:100px;">折旧方法</span><el-select v-model="form.depreciation_method" style="width:100%"><el-option label="年限平均法" value="年限平均法" /></el-select></div>
          </div>
        </div>
        <div class="fa-group" style="border-left-color:var(--success);">
          <div class="fa-group-header">
            <span class="fa-group-tag" style="background:var(--success-light);color:var(--success);">时间状态</span>
          </div>
          <div class="fa-group-body">
            <div class="fa-field"><span class="fa-label" style="min-width:100px;">开始折旧日</span><el-date-picker v-model="form.start_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" style="width:100%" /></div>
            <div class="fa-field"><span class="fa-label" style="min-width:100px;">累计折旧</span><el-input-number v-model="form.accumulated_depreciation" :min="0" :precision="2" style="width:100%" controls-position="right" /></div>
            <div class="fa-field"><span class="fa-label" style="min-width:100px;">状态</span><el-select v-model="form.status" style="width:100%"><el-option label="在用" value="在用" /><el-option label="停用" value="停用" /><el-option label="报废" value="报废" /></el-select></div>
          </div>
        </div>
      </el-form>
      <template #footer><el-button @click="dialogVisible = false">取消</el-button><el-button type="primary" @click="handleSave">{{ isEdit ? '保存' : '确认入账' }}</el-button></template>
    </el-dialog>

    <el-dialog v-model="disposeDialogVisible" title="处置固定资产" width="460px">
      <div v-if="disposingAsset">
        <p style="margin-bottom:12px;font-size:13px;color:var(--text-secondary);">资产: {{ disposingAsset.name }} ({{ disposingAsset.asset_code }})</p>
        <el-form label-width="0">
          <div class="fg" style="border-left-color:var(--warning);">
            <div class="fgh"><span class="fgt" style="background:var(--warning-light);color:var(--warning);">处置信息</span></div>
            <div class="fgb">
              <div class="ff"><span class="fl" style="min-width:80px;">处置日期</span><el-date-picker v-model="disposeForm.disposal_date" type="date" value-format="YYYY-MM-DD" style="width:100%;" /></div>
              <div class="ff"><span class="fl" style="min-width:80px;">处置价格</span><el-input-number v-model="disposeForm.disposal_price" :min="0" :precision="2" style="width:100%;" controls-position="right" /></div>
            </div>
          </div>
        </el-form>
      </div>
      <template #footer><el-button @click="disposeDialogVisible=false">取消</el-button><el-button type="warning" @click="confirmDispose">确认处置</el-button></template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import fixedAssetsApi from '../api/fixedAssets'
import { formatMoney } from '../utils/format'
import AccountingTip from './AccountingTip.vue'
import { useAccountAwareData } from '../composables/useAccountAwareData'
import { handleError } from '../api/index'

const list = ref([])
const loading = ref(false)
const statusFilter = ref('')
const dialogVisible = ref(false)
const isEdit = ref(false)
const editingId = ref(null)
const depreciatePeriod = ref(new Date().toISOString().slice(0, 7))
const depreciating = ref(false)
const disposeDialogVisible = ref(false)
const disposingAsset = ref(null)
const disposeForm = ref({ disposal_price: 0, disposal_date: new Date().toISOString().slice(0, 10) })

const defaultForm = () => ({
  asset_code: '', name: '', category: '', original_value: 0,
  salvage_rate: 0.05, useful_life: 12, depreciation_method: '年限平均法',
  start_date: new Date().toISOString().slice(0, 10),
  accumulated_depreciation: 0, status: '在用'
})
const form = ref(defaultForm())

const totalOriginal = computed(() => list.value.reduce((s, a) => s + (Number(a.original_value) || 0), 0))
const totalDepreciation = computed(() => list.value.reduce((s, a) => s + (Number(a.accumulated_depreciation) || 0), 0))
const totalNet = computed(() => totalOriginal.value - totalDepreciation.value)

async function loadData() {
  loading.value = true
  try {
    const params = {}
    if (statusFilter.value) params.status = statusFilter.value
    const res = await fixedAssetsApi.getFixedAssets(params)
    list.value = res.items || res
  } catch (e) {
    handleError(e, { defaultMsg: '加载固定资产列表失败，请检查网络连接' })
  } finally {
    loading.value = false
  }
}

function showCreate() {
  isEdit.value = false
  editingId.value = null
  form.value = defaultForm()
  dialogVisible.value = true
}

function showEdit(row) {
  isEdit.value = true
  editingId.value = row.id
  form.value = { ...row }
  dialogVisible.value = true
}

async function handleSave() {
  try {
    if (isEdit.value) {
      await fixedAssetsApi.updateFixedAsset(editingId.value, form.value)
      ElMessage.success('更新成功')
    } else {
      await fixedAssetsApi.createFixedAsset(form.value)
      ElMessage.success('创建成功')
    }
    dialogVisible.value = false
    loadData()
  } catch (e) {
    handleError(e, { defaultMsg: '保存固定资产失败，请检查输入数据是否正确' })
  }
}

function showDispose(row) {
  disposingAsset.value = row
  disposeForm.value = { disposal_price: 0, disposal_date: new Date().toISOString().slice(0, 10) }
  disposeDialogVisible.value = true
}

async function confirmDispose() {
  try {
    await fixedAssetsApi.disposeFixedAsset(disposingAsset.value.id, disposeForm.value.disposal_price, disposeForm.value.disposal_date)
    ElMessage.success('资产已处置')
    disposeDialogVisible.value = false
    loadData()
  } catch (e) {
    handleError(e, { defaultMsg: '处置固定资产失败，请检查该资产是否已处置' })
  }
}

async function handleDepreciate(row) {
  try {
    const period = depreciatePeriod.value
    const res = await fixedAssetsApi.depreciateFixedAsset(row.id, period)
    ElMessage.success(res.message || '折旧计提成功')
    loadData()
  } catch (e) {
    handleError(e, { defaultMsg: '计提折旧失败' })
  }
}

async function handleBatchDepreciate() {
  if (!depreciatePeriod.value) { ElMessage.warning('请选择折旧期间'); return }
  depreciating.value = true
  try {
    const res = await fixedAssetsApi.batchDepreciateFixedAssets(depreciatePeriod.value)
    ElMessage.success(`批量折旧完成: ${res.count}项资产已计提`)
    loadData()
  } catch (e) {
    handleError(e, { defaultMsg: '批量计提折旧失败' })
  } finally {
    depreciating.value = false
  }
}

function statusType(status) {
  const map = { '在用': 'success', '停用': 'warning', '报废': 'danger' }
  return map[status] || 'info'
}

useAccountAwareData(loadData)
</script>

<style scoped>
.fixed-assets-tab { padding: 0; }
.row { display:flex; gap:12px; }
.c4 { flex:1; }
.stat-mini { background:var(--bg-card); border:1px solid var(--border-lighter); border-left:4px solid var(--primary); border-radius:12px; padding:14px 16px; }
.stat-mini-label { display:block; font-size:12px; color:var(--text-secondary); font-weight:500; margin-bottom:4px; }
.stat-mini-value { font-size:24px; font-weight:700; letter-spacing:-0.5px; }
.fa-group { background: var(--bg-elevated); border: 1px solid var(--border-lighter); border-left: 4px solid; border-radius: 12px; overflow: hidden; margin-bottom: 16px; }
.fa-group-header { padding: 12px 16px 4px; }
.fa-group-tag { display: inline-block; padding: 2px 12px; border-radius: 9999px; font-size: 12px; font-weight: 600; letter-spacing: 0.5px; }
.fa-group-body { padding: 4px 16px 12px; display: flex; flex-direction: column; gap: 10px; }
.fa-field { display: flex; align-items: center; gap: 12px; }
.fa-label { font-size: 13px; color: var(--text-regular); flex-shrink: 0; }
.fg { background:var(--bg-elevated); border:1px solid var(--border-light); border-left:4px solid; border-radius:12px; overflow:hidden; }
.fgh { padding:12px 16px 4px; }
.fgt { display:inline-block; padding:2px 12px; border-radius:9999px; font-size:12px; font-weight:600; }
.fgb { padding:4px 16px 12px; display:flex; flex-direction:column; gap:10px; }
.ff { display:flex; align-items:center; gap:12px; }
.fl { font-size:13px; color:var(--text-regular); flex-shrink:0; }
</style>
